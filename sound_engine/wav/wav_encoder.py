"""WAV encoding/decoding utilities using stdlib only (except mp3_to_wav which needs pydub)."""
import io
import struct
import wave
from typing import List


def encode_pcm_to_wav(samples: List[int], sample_rate: int = 16000, num_channels: int = 1, sampwidth: int = 2) -> bytes:
    """Encode raw PCM samples (list of ints) to WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        raw = struct.pack(f'<{len(samples)}h', *samples)
        wf.writeframes(raw)
    return buf.getvalue()


def encode_raw_pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000, num_channels: int = 1, sampwidth: int = 2) -> bytes:
    """Wrap raw PCM bytes in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def get_duration_ms(wav_bytes: bytes) -> float:
    """Read WAV header and return duration in milliseconds."""
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, 'rb') as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return (frames / rate) * 1000.0


def _mp3_to_wav_miniaudio(mp3_bytes: bytes, sample_rate: int) -> bytes:
    """Decode MP3 → 16-bit mono WAV fully in-process (no ffmpeg subprocess).

    Uses miniaudio (a small self-contained C extension). Raises if miniaudio
    is missing or decoding fails so the caller can fall back to pydub.
    """
    import miniaudio  # raises ImportError if not installed → caller falls back

    decoded = miniaudio.decode(
        mp3_bytes,
        output_format=miniaudio.SampleFormat.SIGNED16,
        nchannels=1,
        sample_rate=sample_rate,
    )
    return encode_raw_pcm_to_wav(
        decoded.samples.tobytes(),
        sample_rate=sample_rate,
        num_channels=1,
        sampwidth=2,
    )


def mp3_to_wav(mp3_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Convert MP3 bytes to WAV bytes.

    Fast path: decode in-process via miniaudio (no per-call ffmpeg subprocess).
    Falls back to pydub/ffmpeg if miniaudio is unavailable or fails, so behaviour
    is never worse than before.
    """
    try:
        return _mp3_to_wav_miniaudio(mp3_bytes, sample_rate)
    except Exception:
        pass  # fall through to pydub/ffmpeg

    try:
        from pydub import AudioSegment
    except ImportError:
        raise RuntimeError("pydub is not installed. Run: pip install pydub")

    try:
        segment = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
    except Exception as e:
        if "ffmpeg" in str(e).lower() or "avconv" in str(e).lower():
            raise RuntimeError(
                "ffmpeg is required for MP3 conversion. Install it and ensure it is on your PATH.\n"
                "  Windows: winget install ffmpeg\n"
                "  macOS:   brew install ffmpeg\n"
                "  Linux:   sudo apt install ffmpeg"
            ) from e
        raise

    segment = segment.set_frame_rate(sample_rate).set_channels(1).set_sample_width(2)
    buf = io.BytesIO()
    segment.export(buf, format="wav")
    return buf.getvalue()
