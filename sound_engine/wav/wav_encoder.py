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


def mp3_to_wav(mp3_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Convert MP3 bytes to WAV bytes using pydub (requires ffmpeg on PATH)."""
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
