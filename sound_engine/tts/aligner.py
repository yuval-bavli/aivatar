"""Word-level forced alignment using faster-whisper.

Runs faster-whisper base.en on TTS-generated WAV with word_timestamps=True,
matches whisper tokens to source words, and returns per-word (start_ms, dur_ms) windows.

Usage:
    aligner = WordAligner()          # loads model once (~3s CPU)
    timings = aligner.align(wav_bytes, "Can you say both?")
    # -> [(start_ms, dur_ms), ...] one per source word, or None on failure
"""

import logging
import re
import struct
import time
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ── WAV parsing ──────────────────────────────────────────────────────────────

def _wav_to_float32(wav_bytes: bytes) -> Tuple[np.ndarray, int]:
    """Parse WAV bytes → float32 mono numpy array at original sample rate.

    Returns (audio_f32, sample_rate).
    """
    if wav_bytes[:4] != b'RIFF':
        raise ValueError("Not a WAV file")

    pos = 12
    sample_rate = 16000
    num_channels = 1
    bits_per_sample = 16
    pcm_bytes: Optional[bytes] = None

    while pos + 8 <= len(wav_bytes):
        chunk_id = wav_bytes[pos:pos + 4]
        chunk_size = struct.unpack_from('<I', wav_bytes, pos + 4)[0]
        pos += 8
        if chunk_id == b'fmt ':
            num_channels = struct.unpack_from('<H', wav_bytes, pos + 2)[0]
            sample_rate = struct.unpack_from('<I', wav_bytes, pos + 4)[0]
            bits_per_sample = struct.unpack_from('<H', wav_bytes, pos + 14)[0]
            pos += chunk_size
        elif chunk_id == b'data':
            pcm_bytes = wav_bytes[pos:pos + chunk_size]
            break
        else:
            pos += chunk_size

    if pcm_bytes is None:
        raise ValueError("No data chunk in WAV")

    if bits_per_sample == 16:
        samples = np.frombuffer(pcm_bytes, dtype='<i2').astype(np.float32) / 32768.0
    else:
        raise ValueError(f"Unsupported bits_per_sample={bits_per_sample}")

    if num_channels > 1:
        samples = samples.reshape(-1, num_channels).mean(axis=1)

    # Resample to 16 kHz if needed (whisper requires 16 kHz)
    if sample_rate != 16000:
        target_len = int(len(samples) * 16000 / sample_rate)
        indices = np.linspace(0, len(samples) - 1, target_len)
        samples = np.interp(indices, np.arange(len(samples)), samples)

    return samples.astype(np.float32), 16000


# ── Word normalisation ────────────────────────────────────────────────────────

_PUNCT = re.compile(r"[.?!,:;'\"\-]+")


def _norm(word: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return _PUNCT.sub("", word).strip().lower()


# ── Main class ────────────────────────────────────────────────────────────────

class WordAligner:
    """
    Post-TTS word-level aligner using faster-whisper base.en.

    Loads the model once on construction. align() is a blocking call;
    wrap in asyncio.to_thread() if calling from async context.
    """

    def __init__(self, device: str = "cpu", model_size: str = "base.en"):
        self._model = None
        self._device = device
        self._model_size = model_size
        self._load_model()

    def _load_model(self) -> None:
        try:
            from faster_whisper import WhisperModel
            compute_type = "int8" if self._device == "cpu" else "float16"
            t0 = time.perf_counter()
            logger.info("Loading faster-whisper '%s' on %s (%s) for alignment…",
                        self._model_size, self._device, compute_type)
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=compute_type,
            )
            logger.info("Aligner model loaded in %.1fs", time.perf_counter() - t0)
        except Exception as e:
            logger.warning("WordAligner: model load failed (%s) — alignment disabled", e)
            self._model = None

    @property
    def available(self) -> bool:
        return self._model is not None

    def align(
        self,
        wav_bytes: bytes,
        source_text: str,
        max_inference_s: float = 5.0,
    ) -> Optional[List[Tuple[float, float]]]:
        """
        Align source_text to wav_bytes using whisper word timestamps.

        Returns:
            List of (start_ms, dur_ms) — one entry per whitespace-split source word.
            None on any failure (caller should fall back to sentence-level timing).
        """
        if not self.available:
            return None

        source_words = [w for w in source_text.split() if w]
        if not source_words:
            return None

        try:
            audio_f32, _sr = _wav_to_float32(wav_bytes)
            duration_ms = len(audio_f32) / 16000 * 1000

            t0 = time.perf_counter()
            segments_gen, _info = self._model.transcribe(
                audio_f32,
                language="en",
                beam_size=1,
                word_timestamps=True,
                vad_filter=False,
            )

            whisper_words = []
            for seg in segments_gen:
                if seg.words:
                    whisper_words.extend(seg.words)

            elapsed = time.perf_counter() - t0
            logger.debug("Whisper alignment: %.0fms audio → %d tokens in %.0fms",
                         duration_ms, len(whisper_words), elapsed * 1000)

            if elapsed > max_inference_s:
                logger.warning("Alignment inference %.1fs > limit %.1fs — disabling for this clip",
                               elapsed, max_inference_s)
                return None

            if not whisper_words:
                logger.debug("Whisper returned no word tokens — falling back")
                return None

            # Use audio_analyzer to find true speech onset, clamping whisper's
            # first word start (whisper sometimes reports onset 50-100ms early).
            speech_onset_ms = self._detect_speech_onset(wav_bytes)
            if speech_onset_ms is not None and whisper_words:
                first_start = whisper_words[0].start * 1000.0
                if first_start < speech_onset_ms:
                    # Shift all timestamps so the first word starts at speech onset
                    shift = speech_onset_ms - first_start
                    logger.debug("Clamping whisper first-word start: %.0f→%.0f ms (shift +%.0f)",
                                 first_start, speech_onset_ms, shift)
                    # We don't mutate the frozen dataclasses; store shift for use below
                else:
                    shift = 0.0
            else:
                shift = 0.0

            return self._match(source_words, whisper_words, duration_ms, shift)

        except Exception as e:
            logger.warning("WordAligner.align failed: %s", e, exc_info=True)
            return None

    def _detect_speech_onset(self, wav_bytes: bytes) -> Optional[float]:
        """Return the start_ms of the first detected speech region, or None."""
        try:
            from sound_engine.audio_analyzer import analyze_wav
            profile = analyze_wav(wav_bytes)
            if profile.speech_regions:
                return profile.speech_regions[0].start_ms
        except Exception:
            pass
        return None

    def _match(
        self,
        source_words: List[str],
        whisper_words,           # list of faster-whisper Word objects
        duration_ms: float,
        shift_ms: float = 0.0,
    ) -> Optional[List[Tuple[float, float]]]:
        """
        Greedy in-order alignment of whisper tokens → source words.

        Handles:
        - Exact count: zip directly.
        - Whisper has more tokens: merge consecutive tokens to cover each source word.
        - Whisper has fewer tokens: distribute source words across nearby token windows.

        Returns None if edit distance between any matched pair exceeds threshold.
        """
        src_norm = [_norm(w) for w in source_words]
        whi_norm = [_norm(w.word) for w in whisper_words]

        n = len(src_norm)
        m = len(whi_norm)

        logger.debug("Align %d src → %d whisper tokens | src=%s | whi=%s",
                     n, m, src_norm, whi_norm)

        # Build assignment: assignment[i] = list of whisper indices for source word i
        assignment: List[List[int]] = [[] for _ in range(n)]

        if n == m:
            for i in range(n):
                assignment[i] = [i]
        elif m > n:
            # Merge whisper tokens into n groups (proportional to position)
            boundaries = [int(round(i * m / n)) for i in range(n + 1)]
            for i in range(n):
                assignment[i] = list(range(boundaries[i], boundaries[i + 1]))
                if not assignment[i]:
                    assignment[i] = [min(boundaries[i], m - 1)]
        else:
            # Fewer whisper tokens than source words — distribute by ratio
            for j in range(m):
                i = min(n - 1, int(j * n / m))
                assignment[i].append(j)
            # Fill empty source-word slots from neighbours
            for i in range(n):
                if not assignment[i]:
                    for d in range(1, n + 1):
                        left = i - d
                        right = i + d
                        if 0 <= left < n and assignment[left]:
                            assignment[i] = [assignment[left][-1]]
                            break
                        if 0 <= right < n and assignment[right]:
                            assignment[i] = [assignment[right][0]]
                            break

        # Validate: check edit distance on the primary (first) matched token
        for i, indices in enumerate(assignment):
            if not indices:
                continue
            best_whi = whi_norm[indices[0]]
            dist = _edit_distance(src_norm[i], best_whi)
            if dist > max(2, len(src_norm[i]) // 2):
                logger.debug("High edit distance %d: src=%r whi=%r — falling back",
                             dist, src_norm[i], best_whi)
                return None

        # Build (start_ms, dur_ms) per source word
        timings: List[Tuple[float, float]] = []
        for i, indices in enumerate(assignment):
            if not indices:
                # Interpolate from previous
                prev_end = timings[-1][0] + timings[-1][1] if timings else 0.0
                timings.append((prev_end, 50.0))
                continue

            raw_start = min(whisper_words[j].start for j in indices) * 1000.0
            raw_end = max(whisper_words[j].end for j in indices) * 1000.0

            # Apply onset shift
            start_ms = max(0.0, raw_start + shift_ms)
            end_ms = min(duration_ms, raw_end + shift_ms)

            dur_ms = max(20.0, end_ms - start_ms)
            timings.append((start_ms, dur_ms))

        return timings


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein edit distance between two strings."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(a) + 1))
    for j, cb in enumerate(b):
        curr = [j + 1]
        for i, ca in enumerate(a):
            curr.append(min(prev[i + 1] + 1, curr[i] + 1,
                            prev[i] + (0 if ca == cb else 1)))
        prev = curr
    return prev[-1]
