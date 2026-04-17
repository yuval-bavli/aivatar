"""Per-WebSocket-connection state machine for STT.

Each WebSocket connection gets its own STTSession instance. The session:
  1. Receives raw PCM audio chunks (int16, 16kHz, mono)
  2. Feeds them through Silero VAD chunk-by-chunk
  3. Tracks LISTENING / SPEAKING state
  4. On speech_end, signals the server to run transcription

The SileroVAD instance is shared across sessions (it's thread-safe for
inference, but each session resets it independently — this is fine because
VAD state reset is per-call and the model itself is stateless between resets).
"""

import logging
from enum import Enum, auto
from typing import Any

import numpy as np

from .audio_buffer import AudioBuffer, SAMPLE_RATE, MAX_UTTERANCE_S
from .vad import SileroVAD, VAD_CHUNK_SAMPLES

logger = logging.getLogger(__name__)

DEFAULT_VAD_SILENCE_MS = 500    # silence duration before speech_end is triggered
DEFAULT_LANGUAGE = "en"


class State(Enum):
    LISTENING = auto()  # waiting for speech to start
    SPEAKING = auto()   # speech in progress, accumulating audio


class STTSession:
    """Per-connection state machine.

    Args:
        vad: Shared SileroVAD instance (loaded once at server startup).
        language: Default transcription language ("en", "he", or "mixed").
        vad_silence_ms: Silence duration in ms before speech_end fires.
    """

    def __init__(
        self,
        vad: SileroVAD,
        language: str = DEFAULT_LANGUAGE,
        vad_silence_ms: int = DEFAULT_VAD_SILENCE_MS,
    ):
        self._vad = vad
        self.language = language
        self.vad_silence_ms = vad_silence_ms

        self._state = State.LISTENING
        self._buffer = AudioBuffer()

        # Silence tracking: count of consecutive silent VAD chunks
        self._silence_chunks = 0
        self._silence_chunks_threshold = self._compute_silence_threshold()

        # Force-end tracking
        self._speaking_samples = 0

        self._vad.reset()

    # ------------------------------------------------------------------
    # Audio processing (called for every binary WebSocket message)
    # ------------------------------------------------------------------

    def process_audio(self, pcm_bytes: bytes) -> list[dict[str, Any]]:
        """Process a raw PCM chunk and return any events to send back.

        Args:
            pcm_bytes: Raw PCM data, int16 little-endian, 16kHz mono.

        Returns:
            List of event dicts. Each dict has at least a "type" key.
            Possible types:
              - {"type": "vad_event", "event": "speech_start"}
              - {"type": "vad_event", "event": "speech_end"}   ← triggers transcription
        """
        chunk = np.frombuffer(pcm_bytes, dtype=np.int16)
        events: list[dict] = []

        # Process through VAD in VAD_CHUNK_SAMPLES-sized windows
        for start in range(0, len(chunk), VAD_CHUNK_SAMPLES):
            sub_chunk = chunk[start:start + VAD_CHUNK_SAMPLES]
            speech_prob = self._vad.process_chunk(sub_chunk)
            is_speech = speech_prob >= self._vad.threshold

            if self._state == State.LISTENING:
                self._buffer.add_pre_buffer(sub_chunk)
                if is_speech:
                    self._transition_to_speaking(events)

            elif self._state == State.SPEAKING:
                force_end = self._buffer.add_utterance(sub_chunk)
                self._speaking_samples += len(sub_chunk)

                if is_speech:
                    self._silence_chunks = 0
                else:
                    self._silence_chunks += 1
                    if (self._silence_chunks >= self._silence_chunks_threshold
                            or force_end):
                        if force_end:
                            logger.info("Max utterance length reached (%.0fs), force-ending",
                                        MAX_UTTERANCE_S)
                        self._transition_to_listening(events)

        return events

    # ------------------------------------------------------------------
    # Control messages (called for JSON WebSocket messages)
    # ------------------------------------------------------------------

    def process_control(self, msg: dict) -> list[dict[str, Any]]:
        """Handle a JSON control message from the client.

        Supported types:
          - {"type": "config", "language": "he", "vad_silence_ms": 600}
          - {"type": "reset"}

        Returns a list of response events (may be empty).
        """
        msg_type = msg.get("type")
        if msg_type == "config":
            if "language" in msg:
                self.language = msg["language"]
                logger.info("Session language set to %s", self.language)
            if "vad_silence_ms" in msg:
                self.vad_silence_ms = int(msg["vad_silence_ms"])
                self._silence_chunks_threshold = self._compute_silence_threshold()
                logger.info("VAD silence threshold set to %dms", self.vad_silence_ms)
            return []

        if msg_type == "reset":
            logger.info("Session reset requested by client")
            self.reset()
            return []

        logger.warning("Unknown control message type: %r", msg_type)
        return [{"type": "error", "message": f"Unknown control type: {msg_type!r}"}]

    # ------------------------------------------------------------------
    # Utterance retrieval (called by server after speech_end event)
    # ------------------------------------------------------------------

    def get_utterance(self) -> np.ndarray | None:
        """Return the accumulated utterance audio as float32, or None if too short."""
        if not self._buffer.is_utterance_above_minimum:
            logger.debug("Utterance too short (%.2fs), ignoring",
                         self._buffer.utterance_duration_s)
            return None
        return self._buffer.get_utterance_float32()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transition_to_speaking(self, events: list) -> None:
        logger.debug("VAD: speech_start")
        self._state = State.SPEAKING
        self._silence_chunks = 0
        self._speaking_samples = 0
        self._buffer.start_utterance()
        events.append({"type": "vad_event", "event": "speech_start"})

    def _transition_to_listening(self, events: list) -> None:
        logger.debug("VAD: speech_end (utterance %.2fs)",
                     self._buffer.utterance_duration_s)
        self._state = State.LISTENING
        self._vad.reset()
        events.append({"type": "vad_event", "event": "speech_end"})
        # Note: server reads the utterance via get_utterance() after this event

    def _compute_silence_threshold(self) -> int:
        """Convert vad_silence_ms into a count of VAD_CHUNK_SAMPLES chunks."""
        chunk_ms = VAD_CHUNK_SAMPLES / SAMPLE_RATE * 1000
        return max(1, int(self.vad_silence_ms / chunk_ms))

    def reset(self) -> None:
        """Hard reset — return to LISTENING, clear all buffers."""
        self._state = State.LISTENING
        self._buffer.reset()
        self._silence_chunks = 0
        self._speaking_samples = 0
        self._vad.reset()
