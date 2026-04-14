"""Offline fallback TTS: generates a 220 Hz sine wave. No external dependencies."""
import math
import struct
import wave
import io
from typing import List, Tuple


class MockTTS:
    """Generates a sine-wave WAV at ~2.5 words/sec. Stdlib only."""

    SAMPLE_RATE = 16000
    FREQUENCY = 220  # Hz

    def synthesize(self, text: str) -> Tuple[bytes, float, List[Tuple[float, float]]]:
        """
        Returns:
            (wav_bytes, duration_ms, word_timings)
            word_timings: [(start_ms, duration_ms), ...] per word
        """
        words = [w for w in text.split() if w]
        words_per_sec = 2.5
        word_dur_ms = 1000.0 / words_per_sec
        total_ms = max(500.0, len(words) * word_dur_ms)

        # Build word timings
        word_timings: List[Tuple[float, float]] = []
        for i in range(len(words)):
            word_timings.append((i * word_dur_ms, word_dur_ms))

        wav_bytes = self._generate_sine(total_ms)
        return wav_bytes, total_ms, word_timings

    def _generate_sine(self, duration_ms: float) -> bytes:
        num_samples = int(self.SAMPLE_RATE * duration_ms / 1000.0)
        # Fade in/out over 50ms to avoid clicks
        fade_samples = int(self.SAMPLE_RATE * 0.05)

        samples = []
        for i in range(num_samples):
            t = i / self.SAMPLE_RATE
            sample = math.sin(2 * math.pi * self.FREQUENCY * t)
            # Apply fade
            if i < fade_samples:
                sample *= i / fade_samples
            elif i > num_samples - fade_samples:
                sample *= (num_samples - i) / fade_samples
            samples.append(int(sample * 16000))  # 16-bit range, ~50% amplitude

        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))
        return buf.getvalue()
