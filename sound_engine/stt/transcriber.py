"""faster-whisper transcription wrapper.

Loads the large-v3-turbo model once on startup, keeps it in VRAM, and
exposes a single synchronous transcribe() call. The caller is responsible
for serializing GPU access via an asyncio.Lock when running in async context.

Model: large-v3-turbo (~3GB VRAM in float16)
Device: CUDA GPU
"""

import logging
import time
from dataclasses import dataclass

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

MODEL_SIZE = "large-v3-turbo"
DEVICE = "cuda"
COMPUTE_TYPE = "float16"


@dataclass
class TranscriptResult:
    text: str
    language: str
    duration_ms: float    # length of the audio that was transcribed
    inference_ms: float   # wall-clock time spent in whisper inference


class WhisperTranscriber:
    """Wraps faster-whisper WhisperModel for single-shot utterance transcription.

    Usage:
        transcriber = WhisperTranscriber()   # loads model (slow, do once)
        result = transcriber.transcribe(audio_f32, language="en")

    This is a synchronous, blocking call. In the async server, run it via
    asyncio.to_thread() while holding a GPU lock so concurrent connections
    don't clobber each other.
    """

    def __init__(
        self,
        model_size: str = MODEL_SIZE,
        device: str = DEVICE,
        compute_type: str = COMPUTE_TYPE,
    ):
        logger.info("Loading faster-whisper model '%s' on %s (%s)...",
                    model_size, device, compute_type)
        t0 = time.perf_counter()
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        elapsed = time.perf_counter() - t0
        logger.info("faster-whisper model loaded in %.1fs", elapsed)
        self.model_size = model_size
        self.device = device

    def transcribe(self, audio: np.ndarray, language: str = "en") -> TranscriptResult:
        """Transcribe a complete utterance.

        Args:
            audio: float32 numpy array, 16kHz mono, values in [-1, 1].
            language: BCP-47 language code, e.g. "en" or "he", or "mixed"
                      to let Whisper auto-detect language per segment (useful
                      for Hebrew/English code-switching).

        Returns:
            TranscriptResult with the joined segment text.
        """
        duration_ms = len(audio) / 16000 * 1000

        # "mixed": detect language restricted to en/he, then transcribe with winner
        if language == "mixed":
            _, _top_prob, all_probs = self._model.detect_language(audio)
            probs = dict(all_probs)
            whisper_language = "he" if probs.get("he", 0) > probs.get("en", 0) else "en"
            logger.debug("Mixed mode detected language: %s (en=%.2f, he=%.2f)",
                         whisper_language, probs.get("en", 0), probs.get("he", 0))
        else:
            whisper_language = language

        t0 = time.perf_counter()
        segments, _info = self._model.transcribe(
            audio,
            language=whisper_language,
            beam_size=1,        # greedy — fastest, fine for conversational speech
            vad_filter=False,   # we already ran our own VAD
        )

        # Consume the generator and join all segment texts
        parts = [seg.text for seg in segments]
        text = " ".join(parts).strip()

        inference_ms = (time.perf_counter() - t0) * 1000
        logger.debug("Transcribed %.0fms audio in %.0fms: %r",
                     duration_ms, inference_ms, text[:80])

        return TranscriptResult(
            text=text,
            language=language,
            duration_ms=duration_ms,
            inference_ms=inference_ms,
        )
