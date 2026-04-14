"""
WAV audio analysis for lip sync ground-truth timing extraction.

Computes RMS energy in 10 ms windows, detects speech/silence regions,
and finds local energy peaks — all without scipy (stdlib + optional numpy).
"""

import struct
import math
from dataclasses import dataclass, field
from typing import List, Tuple


# ──────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────

@dataclass
class EnergyWindow:
    time_ms: float
    rms: float


@dataclass
class Region:
    start_ms: float
    end_ms: float

    @property
    def duration_ms(self) -> float:
        return self.end_ms - self.start_ms


@dataclass
class AudioProfile:
    """Results of WAV analysis."""
    sample_rate: int
    duration_ms: float
    rms_windows: List[EnergyWindow]          # 10 ms bins
    speech_regions: List[Region]             # continuous stretches above threshold
    silence_regions: List[Region]            # continuous stretches below threshold
    peaks: List[float]                       # time_ms of local energy maxima


# ──────────────────────────────────────────────
# WAV header parsing
# ──────────────────────────────────────────────

def _parse_wav(wav_bytes: bytes) -> Tuple[int, int, bytes]:
    """
    Returns (sample_rate, num_channels, pcm_bytes).
    Handles standard PCM WAV with variable-size header by scanning for 'data' chunk.
    """
    if len(wav_bytes) < 44:
        raise ValueError("WAV too short")

    # RIFF header
    if wav_bytes[:4] != b'RIFF':
        raise ValueError("Not a RIFF file")
    if wav_bytes[8:12] != b'WAVE':
        raise ValueError("Not a WAVE file")

    # Scan chunks
    pos = 12
    sample_rate = 44100
    num_channels = 1
    bits_per_sample = 16

    while pos + 8 <= len(wav_bytes):
        chunk_id = wav_bytes[pos:pos+4]
        chunk_size = struct.unpack_from('<I', wav_bytes, pos+4)[0]
        pos += 8

        if chunk_id == b'fmt ':
            audio_format = struct.unpack_from('<H', wav_bytes, pos)[0]
            num_channels = struct.unpack_from('<H', wav_bytes, pos+2)[0]
            sample_rate = struct.unpack_from('<I', wav_bytes, pos+4)[0]
            bits_per_sample = struct.unpack_from('<H', wav_bytes, pos+14)[0]
            pos += chunk_size
        elif chunk_id == b'data':
            pcm_bytes = wav_bytes[pos:pos+chunk_size]
            return sample_rate, num_channels, pcm_bytes
        else:
            pos += chunk_size

    raise ValueError("No 'data' chunk found in WAV")


def _pcm_to_mono_float(pcm_bytes: bytes, num_channels: int, bits_per_sample: int = 16) -> List[float]:
    """Convert PCM bytes to mono float samples in [-1.0, 1.0]."""
    if bits_per_sample == 16:
        fmt = f'<{len(pcm_bytes)//2}h'
        samples = struct.unpack(fmt, pcm_bytes[:len(pcm_bytes) & ~1])
        scale = 1.0 / 32768.0
    elif bits_per_sample == 8:
        fmt = f'{len(pcm_bytes)}B'
        raw = struct.unpack(fmt, pcm_bytes)
        samples = [(s - 128) for s in raw]
        scale = 1.0 / 128.0
    else:
        raise ValueError(f"Unsupported bits_per_sample={bits_per_sample}")

    if num_channels == 1:
        return [s * scale for s in samples]

    # Mix to mono
    mono = []
    for i in range(0, len(samples), num_channels):
        chunk = samples[i:i+num_channels]
        mono.append(sum(chunk) / num_channels * scale)
    return mono


# ──────────────────────────────────────────────
# RMS computation
# ──────────────────────────────────────────────

def _compute_rms_windows(
    samples: List[float],
    sample_rate: int,
    window_ms: float = 10.0,
) -> List[EnergyWindow]:
    """Compute RMS energy in non-overlapping windows of `window_ms` ms."""
    window_size = max(1, int(sample_rate * window_ms / 1000.0))
    windows: List[EnergyWindow] = []
    n = len(samples)

    for i in range(0, n, window_size):
        chunk = samples[i:i+window_size]
        if not chunk:
            break
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))
        time_ms = (i / sample_rate) * 1000.0
        windows.append(EnergyWindow(time_ms=time_ms, rms=rms))

    return windows


# ──────────────────────────────────────────────
# Speech / silence region detection
# ──────────────────────────────────────────────

def _detect_regions(
    windows: List[EnergyWindow],
    speech_threshold_fraction: float = 0.15,
    min_silence_ms: float = 80.0,
    min_speech_ms: float = 30.0,
) -> Tuple[List[Region], List[Region]]:
    """
    Classify each 10 ms window as speech or silence using a threshold
    of `speech_threshold_fraction` × peak RMS.

    Short gaps/bursts below `min_silence_ms` / `min_speech_ms` are merged
    to avoid fragmented regions.
    """
    if not windows:
        return [], []

    peak = max(w.rms for w in windows)
    threshold = peak * speech_threshold_fraction

    # Raw labels
    labels = ['speech' if w.rms >= threshold else 'silence' for w in windows]

    # Merge short gaps
    min_silence_bins = max(1, int(min_silence_ms / 10.0))
    min_speech_bins = max(1, int(min_speech_ms / 10.0))

    def _merge(labels_in, short_len, majority):
        """Flip runs of `majority` shorter than `short_len` to the other label."""
        out = list(labels_in)
        i = 0
        while i < len(out):
            if out[i] == majority:
                j = i
                while j < len(out) and out[j] == majority:
                    j += 1
                if (j - i) < short_len:
                    other = 'speech' if majority == 'silence' else 'silence'
                    for k in range(i, j):
                        out[k] = other
                i = j
            else:
                i += 1
        return out

    labels = _merge(labels, min_silence_bins, 'silence')
    labels = _merge(labels, min_speech_bins, 'speech')

    # Build regions
    speech_regions: List[Region] = []
    silence_regions: List[Region] = []

    i = 0
    while i < len(labels):
        label = labels[i]
        j = i
        while j < len(labels) and labels[j] == label:
            j += 1
        start_ms = windows[i].time_ms
        end_ms = windows[j - 1].time_ms + 10.0
        region = Region(start_ms=start_ms, end_ms=end_ms)
        if label == 'speech':
            speech_regions.append(region)
        else:
            silence_regions.append(region)
        i = j

    return speech_regions, silence_regions


# ──────────────────────────────────────────────
# Peak detection
# ──────────────────────────────────────────────

def _find_peaks(
    windows: List[EnergyWindow],
    min_peak_fraction: float = 0.3,
    neighborhood_ms: float = 60.0,
) -> List[float]:
    """
    Find local RMS maxima that exceed `min_peak_fraction` of the global max.
    Each peak must be the maximum within ±`neighborhood_ms`.
    Returns list of time_ms values.
    """
    if not windows:
        return []

    peak_rms = max(w.rms for w in windows)
    threshold = peak_rms * min_peak_fraction
    neighborhood_bins = max(1, int(neighborhood_ms / 10.0))

    peaks: List[float] = []
    n = len(windows)

    for i, w in enumerate(windows):
        if w.rms < threshold:
            continue
        lo = max(0, i - neighborhood_bins)
        hi = min(n, i + neighborhood_bins + 1)
        neighborhood_max = max(windows[k].rms for k in range(lo, hi))
        if w.rms >= neighborhood_max:
            peaks.append(w.time_ms)

    return peaks


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def analyze_wav(wav_bytes: bytes, window_ms: float = 10.0) -> AudioProfile:
    """
    Analyze a WAV file and return an AudioProfile with:
    - rms_windows: RMS energy in `window_ms` bins
    - speech_regions / silence_regions: contiguous activity segments
    - peaks: time positions (ms) of local energy maxima

    Args:
        wav_bytes: Raw WAV file bytes (must be PCM, 16-bit LE recommended)
        window_ms: Analysis window size in milliseconds (default 10 ms)

    Returns:
        AudioProfile
    """
    sample_rate, num_channels, pcm_bytes = _parse_wav(wav_bytes)
    samples = _pcm_to_mono_float(pcm_bytes, num_channels)

    duration_ms = (len(samples) / sample_rate) * 1000.0

    rms_windows = _compute_rms_windows(samples, sample_rate, window_ms)
    speech_regions, silence_regions = _detect_regions(rms_windows)
    peaks = _find_peaks(rms_windows)

    return AudioProfile(
        sample_rate=sample_rate,
        duration_ms=duration_ms,
        rms_windows=rms_windows,
        speech_regions=speech_regions,
        silence_regions=silence_regions,
        peaks=peaks,
    )


def rms_at_ms(profile: AudioProfile, time_ms: float) -> float:
    """Look up RMS value at a given time (nearest 10 ms bin)."""
    if not profile.rms_windows:
        return 0.0
    idx = min(len(profile.rms_windows) - 1, int(time_ms / 10.0))
    return profile.rms_windows[idx].rms


def is_speech_at(profile: AudioProfile, time_ms: float) -> bool:
    """Return True if the given time falls within a detected speech region."""
    for r in profile.speech_regions:
        if r.start_ms <= time_ms < r.end_ms:
            return True
    return False
