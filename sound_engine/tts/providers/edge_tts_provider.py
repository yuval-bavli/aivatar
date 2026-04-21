"""Free TTS via Microsoft Edge voices using the edge-tts library."""
import asyncio
import re
from typing import List, Optional, Tuple

from ...wav.wav_encoder import mp3_to_wav, get_duration_ms


def _split_words(text: str) -> List[str]:
    """Tokenize text into words (strip punctuation, keep apostrophes)."""
    return [w for w in re.split(r"\s+", text.strip()) if w]


class EdgeTTSProvider:
    """
    Wraps edge-tts to synthesize speech and capture timing events.

    edge-tts v7+ emits SentenceBoundary (not WordBoundary) events.
    We return the raw sentence windows; actual per-word distribution happens
    in VisemeScheduler, where it can weight by phoneme count.

    Returns WAV bytes, duration, and a list of (sentence_text, start_ms, dur_ms).
    """

    DEFAULT_VOICE = "en-US-AriaNeural"
    TICKS_TO_MS = 1.0 / 10_000.0  # 100ns ticks → ms

    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice

    async def synthesize_async(self, text: str) -> Tuple[bytes, float, List[Tuple[str, float, float]]]:
        """
        Returns:
            (wav_bytes, duration_ms, sentence_boundaries)
            sentence_boundaries: [(sentence_text, start_ms, duration_ms), ...]

        For v6 WordBoundary events, each boundary is emitted as a single-word
        "sentence" so the downstream code handles both uniformly.
        """
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError("edge-tts is not installed. Run: pip install edge-tts")

        mp3_chunks: List[bytes] = []
        sentence_boundaries: List[Tuple[str, float, float]] = []  # (text, start_ms, dur_ms)

        communicate = edge_tts.Communicate(text, self.voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # v6 style — each word becomes a single-word boundary
                word = chunk.get("text", "")
                start_ms = chunk.get("offset", 0) * self.TICKS_TO_MS
                dur_ms = chunk.get("duration", 0) * self.TICKS_TO_MS
                sentence_boundaries.append((word, start_ms, dur_ms))
            elif chunk["type"] == "SentenceBoundary":
                # v7 style — the scheduler will split the sentence into words
                sent_text = chunk.get("text", "")
                start_ms = chunk.get("offset", 0) * self.TICKS_TO_MS
                dur_ms = chunk.get("duration", 0) * self.TICKS_TO_MS
                sentence_boundaries.append((sent_text, start_ms, dur_ms))

        if not mp3_chunks:
            raise RuntimeError("edge-tts returned no audio data")

        mp3_bytes = b"".join(mp3_chunks)
        wav_bytes = mp3_to_wav(mp3_bytes)
        duration_ms = get_duration_ms(wav_bytes)

        return wav_bytes, duration_ms, sentence_boundaries

    def synthesize(self, text: str) -> Tuple[bytes, float, List[Tuple[str, float, float]]]:
        """Synchronous wrapper around synthesize_async."""
        return asyncio.run(self.synthesize_async(text))
