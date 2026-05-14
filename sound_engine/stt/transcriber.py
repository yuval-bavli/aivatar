"""faster-whisper transcription wrapper.

Loads the whisper model once on startup and exposes a single
synchronous transcribe() call. Device is auto-detected: CUDA if available,
otherwise CPU (with int8 compute for efficiency).

Model selection:
  - Set WHISPER_MODEL env var to override (e.g. "tiny", "base", "large-v3-turbo").
  - Default: "large-v3-turbo" on GPU, "tiny" on CPU (CPU inference is ~10x slower;
    large-v3-turbo takes 10-12s per utterance on CPU which causes client timeouts).
"""

import logging
import os
import time
from dataclasses import dataclass

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

_DEFAULT_GPU_MODEL = "large-v3-turbo"
_DEFAULT_CPU_MODEL = "tiny"


def _detect_device() -> tuple[str, str]:
    """Return (device, compute_type) based on hardware availability."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", "float16"
    except ImportError:
        pass
    return "cpu", "int8"


DEVICE, COMPUTE_TYPE = _detect_device()
MODEL_SIZE = os.environ.get("WHISPER_MODEL") or (
    _DEFAULT_GPU_MODEL if DEVICE == "cuda" else _DEFAULT_CPU_MODEL
)


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
