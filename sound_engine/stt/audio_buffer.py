"""Audio buffer management for the STT pipeline.

Maintains two buffers:
- Pre-speech ring buffer: rolling window of the last ~300ms of audio captured
  while in LISTENING state, so we don't clip the start of a word.
- Utterance buffer: accumulates audio from speech_start through speech_end.
  The pre-speech buffer is prepended when an utterance begins.
"""

import logging
from collections import deque

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000          # Hz — must match incoming audio
PRE_BUFFER_S = 0.3           # seconds of audio to keep before speech starts
MAX_UTTERANCE_S = 30.0       # force-end transcription after this many seconds
MIN_UTTERANCE_S = 0.3        # ignore utterances shorter than this (clicks, pops)

_PRE_BUFFER_SAMPLES = int(PRE_BUFFER_S * SAMPLE_RATE)
_MAX_UTTERANCE_SAMPLES = int(MAX_UTTERANCE_S * SAMPLE_RATE)


class AudioBuffer:
    """Manages pre-speech buffering and utterance accumulation.

    Usage:
        buf = AudioBuffer()
        # While LISTENING:
        buf.add_pre_buffer(chunk)
        # On speech_start:
        buf.start_utterance()
        # While SPEAKING:
        buf.add_utterance(chunk)
        # On speech_end:
        audio = buf.get_utterance_float32()
        buf.reset()
    """

    def __init__(self):
        # Ring buffer storing int16 chunks; total kept <= _PRE_BUFFER_SAMPLES
        self._pre_buffer: deque[np.ndarray] = deque()
        self._pre_buffer_size = 0  # total samples currently in deque

        # Flat list of int16 chunks accumulated during speech
        self._utterance_chunks: list[np.ndarray] = []
        self._utterance_samples = 0

    # ------------------------------------------------------------------
    # Pre-speech ring buffer (call while LISTENING)
    # ------------------------------------------------------------------

    def add_pre_buffer(self, chunk: np.ndarray) -> None:
        """Add a chunk to the rolling pre-speech buffer.

        Args:
            chunk: int16 numpy array of audio samples.
        """
        self._pre_buffer.append(chunk)
        self._pre_buffer_size += len(chunk)

        # Trim oldest chunks until we're within budget
        while self._pre_buffer_size - len(self._pre_buffer[0]) >= _PRE_BUFFER_SAMPLES:
            removed = self._pre_buffer.popleft()
            self._pre_buffer_size -= len(removed)

    # ------------------------------------------------------------------
    # Utterance accumulation (call on speech_start + while SPEAKING)
    # ------------------------------------------------------------------

    def start_utterance(self) -> None:
        """Begin a new utterance, prepending the pre-speech buffer."""
        self._utterance_chunks = []
        self._utterance_samples = 0

        if self._pre_buffer:
            pre = np.concatenate(list(self._pre_buffer))
            self._utterance_chunks.append(pre)
            self._utterance_samples += len(pre)
            logger.debug("Utterance started with %dms pre-buffer",
                         int(len(pre) / SAMPLE_RATE * 1000))

    def add_utterance(self, chunk: np.ndarray) -> bool:
        """Append a chunk to the utterance buffer.

        Returns:
            True if the utterance has hit MAX_UTTERANCE_S (caller should
            force-end), False otherwise.
        """
        self._utterance_chunks.append(chunk)
        self._utterance_samples += len(chunk)
        return self._utterance_samples >= _MAX_UTTERANCE_SAMPLES

    # ------------------------------------------------------------------
    # Retrieval and state
    # ------------------------------------------------------------------

    def get_utterance_float32(self) -> np.ndarray:
        """Return accumulated utterance as float32 normalized to [-1, 1].

        Returns an empty array if no utterance data exists.
        """
        if not self._utterance_chunks:
            return np.array([], dtype=np.float32)
        audio_int16 = np.concatenate(self._utterance_chunks)
        return audio_int16.astype(np.float32) / 32768.0

    @property
    def utterance_duration_s(self) -> float:
        """Current accumulated utterance length in seconds."""
        return self._utterance_samples / SAMPLE_RATE

    @property
    def is_utterance_above_minimum(self) -> bool:
        """True if the utterance is long enough to be worth transcribing."""
        return self.utterance_duration_s >= MIN_UTTERANCE_S

    def reset(self) -> None:
        """Clear all buffers (call after transcription is sent)."""
        self._pre_buffer.clear()
        self._pre_buffer_size = 0
        self._utterance_chunks = []
        self._utterance_samples = 0
