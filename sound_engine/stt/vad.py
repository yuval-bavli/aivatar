"""Silero VAD wrapper for voice activity detection.

Silero VAD runs on CPU and is lightweight enough to process audio in real-time
without a GPU. It expects 16kHz mono audio in fixed-size chunks of 512 samples
(32ms per chunk).

Reference: https://github.com/snakers4/silero-vad
"""

import logging

import numpy as np
import torch

logger = logging.getLogger(__name__)

# Silero VAD requires exactly 512 samples per chunk at 16kHz
VAD_CHUNK_SAMPLES = 512
SAMPLE_RATE = 16000
SPEECH_THRESHOLD = 0.5  # probability above which audio is considered speech


class SileroVAD:
    """Wrapper around the Silero VAD model.

    The model runs on CPU and is shared across all WebSocket sessions.
    Each session calls reset() between utterances to clear internal state.

    Usage:
        vad = SileroVAD()  # loads model once
        prob = vad.process_chunk(chunk_int16)  # returns 0.0–1.0
        if prob > vad.threshold:
            # speech detected
    """

    def __init__(self, threshold: float = SPEECH_THRESHOLD):
        self.threshold = threshold
        logger.info("Loading Silero VAD model...")
        self._model, self._utils = torch.hub.load(
            "snakers4/silero-vad",
            "silero_vad",
            trust_repo=True,
        )
        self._model.eval()
        # get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks
        self.reset()
        logger.info("Silero VAD model loaded (CPU)")

    def process_chunk(self, chunk_int16: np.ndarray) -> float:
        """Run VAD on a chunk of audio.

        If the chunk is larger than VAD_CHUNK_SAMPLES, it is split and the
        maximum probability across sub-chunks is returned (conservative: any
        speech in the window counts as speech).

        Args:
            chunk_int16: int16 numpy array at 16kHz.

        Returns:
            Speech probability in [0.0, 1.0].
        """
        # Normalize to float32 [-1, 1]
        audio_f32 = chunk_int16.astype(np.float32) / 32768.0

        if len(audio_f32) <= VAD_CHUNK_SAMPLES:
            # Pad to exactly VAD_CHUNK_SAMPLES if needed
            if len(audio_f32) < VAD_CHUNK_SAMPLES:
                audio_f32 = np.pad(audio_f32, (0, VAD_CHUNK_SAMPLES - len(audio_f32)))
            return self._infer(audio_f32)

        # Split into VAD_CHUNK_SAMPLES windows, return max probability
        max_prob = 0.0
        for start in range(0, len(audio_f32), VAD_CHUNK_SAMPLES):
            sub = audio_f32[start:start + VAD_CHUNK_SAMPLES]
            if len(sub) < VAD_CHUNK_SAMPLES:
                sub = np.pad(sub, (0, VAD_CHUNK_SAMPLES - len(sub)))
            prob = self._infer(sub)
            if prob > max_prob:
                max_prob = prob
        return max_prob

    def _infer(self, audio_f32: np.ndarray) -> float:
        """Run model inference on exactly VAD_CHUNK_SAMPLES of float32 audio."""
        tensor = torch.from_numpy(audio_f32).unsqueeze(0)  # [1, 512]
        with torch.no_grad():
            prob = self._model(tensor, SAMPLE_RATE).item()
        return float(prob)

    def reset(self) -> None:
        """Reset the VAD model's internal hidden state.

        Call between utterances to avoid state leaking across turns.
        """
        self._model.reset_states()
