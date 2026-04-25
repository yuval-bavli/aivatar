"""Phoneme-level forced alignment using torchaudio MMS_FA.

Strategy:
  1. Run MMS_FA on the TTS-generated WAV → per-character TokenSpan from actual audio.
  2. Group character spans by word to get tight word boundaries from the real audio.
  3. Within each word, distribute ARPABET phonemes by character-span durations so
     phonemes with longer character segments (e.g. long vowels) get more time.

Advantages over the faster-whisper WordAligner:
  - GPU inference: ~80–150ms vs ~400ms (CPU whisper)
  - Forced alignment never hallucinates — it aligns the supplied transcript
  - Character-level resolution within words improves within-word phoneme placement

Fallback chain: PhonemeAligner → WordAligner → sentence-level (unchanged).
"""

import logging
import re
import struct
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Phonemes that typically correspond to 2 characters in English spelling (e.g. TH, SH…)
_MULTI_CHAR_PHONEMES = frozenset({'TH', 'SH', 'CH', 'ZH', 'NG', 'DH', 'HH'})


# ── WAV parsing ───────────────────────────────────────────────────────────────

def _wav_to_float32(wav_bytes: bytes) -> Tuple[np.ndarray, int]:
    """Parse WAV bytes → float32 mono numpy at original sample rate."""
    if wav_bytes[:4] != b'RIFF':
        raise ValueError("Not a WAV file")
    pos = 12
    sample_rate, num_channels, bits = 16000, 1, 16
    pcm_bytes = None
    while pos + 8 <= len(wav_bytes):
        chunk_id = wav_bytes[pos:pos + 4]
        chunk_size = struct.unpack_from('<I', wav_bytes, pos + 4)[0]
        pos += 8
        if chunk_id == b'fmt ':
            num_channels = struct.unpack_from('<H', wav_bytes, pos + 2)[0]
            sample_rate = struct.unpack_from('<I', wav_bytes, pos + 4)[0]
            bits = struct.unpack_from('<H', wav_bytes, pos + 14)[0]
            pos += chunk_size
        elif chunk_id == b'data':
            pcm_bytes = wav_bytes[pos:pos + chunk_size]
            break
        else:
            pos += chunk_size
    if pcm_bytes is None:
        raise ValueError("No data chunk")
    if bits != 16:
        raise ValueError(f"Unsupported bits_per_sample={bits}")
    samples = np.frombuffer(pcm_bytes, dtype='<i2').astype(np.float32) / 32768.0
    if num_channels > 1:
        samples = samples.reshape(-1, num_channels).mean(axis=1)
    if sample_rate != 16000:
        n = int(len(samples) * 16000 / sample_rate)
        samples = np.interp(np.linspace(0, len(samples) - 1, n),
                            np.arange(len(samples)), samples)
    return samples.astype(np.float32), 16000


def _clean_word(w: str) -> str:
    """Lowercase, keep only chars in MMS_FA vocab (a-z, apostrophe, hyphen)."""
    return re.sub(r"[^a-z'-]", '', w.lower())


# ── Main class ────────────────────────────────────────────────────────────────

class PhonemeAligner:
    """
    Forced phoneme aligner backed by torchaudio MMS_FA.

    Public API:
        aligner = PhonemeAligner(device='cuda')
        phoneme_timings = aligner.align(wav_bytes, word_phonemes)
        # -> list[(start_ms, end_ms)] per ARPABET phoneme (flat), or None
    """

    # MMS_FA stride: 320 samples at 16kHz = 20ms per frame
    _HOP_MS = 20.0

    def __init__(self, device: str = 'cuda'):
        self._device = device
        self._model = None
        self._tokenizer = None
        self._aligner_fn = None
        self._load()

    def _load(self) -> None:
        try:
            import torch
            import torchaudio
            bundle = torchaudio.pipelines.MMS_FA
            t0 = time.perf_counter()
            logger.info("Loading MMS_FA on %s …", self._device)
            self._model = bundle.get_model(with_star=False).to(self._device)
            self._model.eval()
            self._tokenizer = bundle.get_tokenizer()
            self._aligner_fn = bundle.get_aligner()
            logger.info("MMS_FA ready in %.1fs", time.perf_counter() - t0)
        except Exception as exc:
            logger.warning("PhonemeAligner: load failed (%s) — disabled", exc)
            self._model = None

    @property
    def available(self) -> bool:
        return self._model is not None

    def align(
        self,
        wav_bytes: bytes,
        word_phonemes: List[Tuple[str, List[str]]],
        max_latency_s: float = 1.5,
    ) -> Optional[List[Tuple[float, float]]]:
        """
        Forced-align phonemes to the audio.

        Args:
            wav_bytes:      WAV file bytes (16-bit PCM or resampled to 16 kHz).
            word_phonemes:  [(word, [ARPABET, ...]), ...] from Phonemizer.

        Returns:
            Flat list of (start_ms, end_ms) — one entry per ARPABET phoneme across
            all words, in order. None on any failure (caller falls back to word aligner).
        """
        if not self.available or not word_phonemes:
            return None
        try:
            import torch

            audio, _sr = _wav_to_float32(wav_bytes)
            duration_ms = len(audio) / 16000.0 * 1000.0
            waveform = torch.from_numpy(audio).unsqueeze(0).to(self._device)

            t0 = time.perf_counter()
            with torch.inference_mode():
                emission, _ = self._model(waveform)
            emission = emission[0]   # [T, vocab_size]

            # Build per-word flat token lists for the aligner.
            # self._tokenizer(word) → List[List[int]] (per-char, each a 1-elem list)
            # The aligner expects List[List[int]] where each inner list = token ids for ONE WORD.
            aligned_word_indices: List[int] = []
            token_lists: List[List[int]] = []
            for i, (word, _phones) in enumerate(word_phonemes):
                cw = _clean_word(word)
                if not cw:
                    continue
                try:
                    char_tokens = self._tokenizer(cw)         # [[idx], [idx], ...]
                    flat = [t for sub in char_tokens for t in sub]  # [idx, idx, ...]
                    if flat:
                        token_lists.append(flat)
                        aligned_word_indices.append(i)
                except Exception:
                    pass

            if not token_lists:
                return None

            # forced alignment: returns List[List[TokenSpan]]
            # word_char_spans[k] = List[TokenSpan] for the k-th aligned word
            word_char_spans = self._aligner_fn(emission, token_lists)

            elapsed = time.perf_counter() - t0
            logger.debug("MMS_FA: %d words aligned in %.0fms (audio=%.0fms)",
                         len(token_lists), elapsed * 1000, duration_ms)
            if elapsed > max_latency_s:
                logger.warning("PhonemeAligner: %.1fs > limit — discarding", elapsed)
                return None

            # Build per-word time windows from char spans (frame → ms)
            word_windows: Dict[int, Tuple[float, float, List[Tuple[float, float]]]] = {}
            for k, wi in enumerate(aligned_word_indices):
                spans = word_char_spans[k]   # List[TokenSpan]
                if not spans:
                    continue
                char_ms = [(s.start * self._HOP_MS, s.end * self._HOP_MS) for s in spans]
                w_start = char_ms[0][0]
                w_end   = char_ms[-1][1]
                word_windows[wi] = (w_start, w_end, char_ms)

            # Interpolate missing words (e.g. punctuation-only)
            self._fill_gaps(word_windows, len(word_phonemes), duration_ms)

            # Distribute phonemes within each word using char-span weights
            result: List[Tuple[float, float]] = []
            for wi, (word, phones) in enumerate(word_phonemes):
                if not phones:
                    continue
                w_start, w_end, char_ms = word_windows.get(wi, (0.0, 0.0, []))
                spans = self._distribute(phones, char_ms, w_start, w_end)
                result.extend(spans)

            return result if result else None

        except Exception as exc:
            logger.warning("PhonemeAligner.align: %s", exc)
            return None

    # ── helpers ────────────────────────────────────────────────────────────────

    def _fill_gaps(
        self,
        word_windows: Dict[int, Tuple[float, float, List]],
        n_words: int,
        duration_ms: float,
    ) -> None:
        """In-place: fill missing word_windows slots by linear interpolation."""
        for i in range(n_words):
            if i in word_windows:
                continue
            prev_end = 0.0
            next_start = duration_ms
            for j in range(i - 1, -1, -1):
                if j in word_windows:
                    prev_end = word_windows[j][1]
                    break
            for j in range(i + 1, n_words):
                if j in word_windows:
                    next_start = word_windows[j][0]
                    break
            # Count consecutive missing words in [i..n_words)
            run = 0
            for j in range(i, n_words):
                if j not in word_windows:
                    run += 1
                else:
                    break
            slot = max(1.0, (next_start - prev_end) / max(1, run))
            pos = prev_end + slot * sum(
                1 for j in range(i) if j not in word_windows
            )
            word_windows[i] = (pos, pos + slot, [])

    def _distribute(
        self,
        phones: List[str],
        char_ms: List[Tuple[float, float]],
        w_start: float,
        w_end: float,
    ) -> List[Tuple[float, float]]:
        """
        Map ARPABET phoneme list to (start_ms, end_ms) within [w_start, w_end].

        Uses character-span durations as relative weights:
        each phoneme gets time proportional to how many characters it "spans"
        (multi-character phonemes like TH, SH count as 2).
        Then the actual ms positions come from pro-rating those weights against
        the per-character durations measured from the audio.
        """
        n = len(phones)
        w_dur = max(1.0, w_end - w_start)

        if n == 1:
            return [(w_start, w_end)]

        # Assign each phoneme a "char weight" (1 for single-char, 2 for digraphs)
        cw = [2.0 if p.upper() in _MULTI_CHAR_PHONEMES else 1.0 for p in phones]
        total_cw = sum(cw)

        if not char_ms:
            # No character spans — fall back to weighted uniform distribution
            result = []
            cursor = w_start
            for weight in cw:
                dur = (weight / total_cw) * w_dur
                result.append((cursor, cursor + dur))
                cursor += dur
            return result

        # Build cumulative character-duration fractions within the word
        char_durs = [max(1e-3, e - s) for s, e in char_ms]
        total_cd = sum(char_durs)
        cum_cd = [0.0]
        for d in char_durs:
            cum_cd.append(cum_cd[-1] + d)

        # Map phoneme char-weight fractions → audio time via cumulative char durations
        cum_cw = [0.0]
        for weight in cw:
            cum_cw.append(cum_cw[-1] + weight)

        def _frac_to_ms(frac: float) -> float:
            """Convert [0,1] fraction of word's char-weight space → ms."""
            # frac × total_cw = cumulative char-weight position
            cwpos = frac * total_cw
            # Find which char bucket this falls in
            char_frac = cwpos / total_cw  # in [0, 1]
            target_cd = char_frac * total_cd
            # Interpolate within char_durs
            acc = 0.0
            for k, d in enumerate(char_durs):
                if acc + d >= target_cd or k == len(char_durs) - 1:
                    t = (target_cd - acc) / max(1e-3, d)
                    return char_ms[k][0] + t * d
                acc += d
            return w_end

        result = []
        for i in range(n):
            p_start = _frac_to_ms(cum_cw[i] / total_cw)
            p_end   = _frac_to_ms(cum_cw[i + 1] / total_cw)
            # Clamp to word window
            p_start = max(w_start, min(w_end, p_start))
            p_end   = max(p_start + 1.0, min(w_end, p_end))
            result.append((p_start, p_end))

        return result
