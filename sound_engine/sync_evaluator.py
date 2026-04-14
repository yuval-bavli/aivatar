"""
Sync evaluation: compare viseme timeline against audio energy profile.

Produces a SyncReport with:
- global_offset_ms:  how far ahead/behind the viseme timeline is vs audio
- drift_factor:      ratio of timeline duration to actual speech duration
                     (>1.0 = timeline too slow / stretched; <1.0 = too fast)
- issues:            human-readable diagnostic strings
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math

from .audio_analyzer import AudioProfile, EnergyWindow


# ──────────────────────────────────────────────
# Viseme openness table
# How wide-open the mouth is for each Azure viseme ID (0–14)
# ──────────────────────────────────────────────

VISEME_OPENNESS: Dict[int, float] = {
    0:  0.00,   # sil
    1:  0.30,   # PP  (bilabial plosive — closed then burst)
    2:  0.45,   # FF  (labiodental fricative)
    3:  0.50,   # TH  (dental fricative)
    4:  0.35,   # DD  (alveolar plosive)
    5:  0.30,   # kk  (velar plosive)
    6:  0.55,   # CH  (postalveolar affricate)
    7:  0.50,   # SS  (sibilant)
    8:  0.55,   # nn  (nasal)
    9:  0.65,   # RR  (rhotic)
    10: 1.00,   # aa  (open front vowel)
    11: 0.85,   # E   (mid-front vowel)
    12: 0.75,   # ih  (high-front vowel)
    13: 0.90,   # oh  (rounded back vowel)
    14: 0.80,   # ou  (close-back vowel)
}


# ──────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────

@dataclass
class VisemeEventData:
    """Minimal viseme event (matches server JSON keys)."""
    time_ms: float
    viseme_id: int


@dataclass
class SyncReport:
    global_offset_ms: float          # positive = visemes START AFTER audio speech onset (too late)
                                     # negative = visemes START BEFORE audio speech onset (too early)
    drift_factor: float              # 1.0 = perfect, >1 = stretched, <1 = compressed
    expected_openness: List[float]   # per-10ms-bin, 0–1
    issues: List[str] = field(default_factory=list)
    pearson_expected_vs_audio: float = 0.0
    # Onset details for debugging
    audio_onset_ms: float = 0.0
    viseme_onset_ms: float = 0.0
    audio_end_ms: float = 0.0
    viseme_end_ms: float = 0.0


# ──────────────────────────────────────────────
# Signal utilities
# ──────────────────────────────────────────────

def _normalize(signal: List[float]) -> List[float]:
    """Normalize to [0, 1] range; returns all-zeros if flat."""
    mx = max(signal) if signal else 0.0
    if mx < 1e-9:
        return [0.0] * len(signal)
    return [v / mx for v in signal]


def _pearson(a: List[float], b: List[float]) -> float:
    """Pearson correlation coefficient between two equal-length lists."""
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    mean_a = sum(a[:n]) / n
    mean_b = sum(b[:n]) / n
    num = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    denom_a = math.sqrt(sum((a[i] - mean_a) ** 2 for i in range(n)))
    denom_b = math.sqrt(sum((b[i] - mean_b) ** 2 for i in range(n)))
    if denom_a < 1e-9 or denom_b < 1e-9:
        return 0.0
    return num / (denom_a * denom_b)


def _cross_correlate_offset(
    reference: List[float],
    signal: List[float],
    max_lag_bins: int = 50,
) -> int:
    """
    Find the lag (bins) that maximises cross-correlation of signal vs reference.
    Positive lag: signal peaks occur AFTER reference peaks → signal is late.
    Used only for the animation-vs-audio score, not for scheduler offset detection.
    """
    n = min(len(reference), len(signal))
    best_lag = 0
    best_corr = -1e9
    for lag in range(-max_lag_bins, max_lag_bins + 1):
        corr = 0.0
        count = 0
        for i in range(n):
            j = i + lag
            if 0 <= j < n:
                corr += reference[i] * signal[j]
                count += 1
        if count > 0:
            corr /= count
        if corr > best_corr:
            best_corr = corr
            best_lag = lag
    return best_lag


# ──────────────────────────────────────────────
# Onset-based offset detection
#
# Much more reliable than cross-correlation for scheduler timing.
# Compares when speech first starts in the audio (detected by RMS threshold)
# versus when the first non-silence viseme is scheduled.
# ──────────────────────────────────────────────

def _measure_onset_offset(
    events: List[VisemeEventData],
    audio_profile: AudioProfile,
) -> Tuple[float, float, float, float]:
    """
    Returns (global_offset_ms, audio_onset_ms, viseme_onset_ms,
             audio_end_ms, viseme_end_ms) using speech-onset comparison.

    global_offset_ms > 0: visemes start AFTER audio speech (too late)
    global_offset_ms < 0: visemes start BEFORE audio speech (too early)
    """
    # Audio speech onset / end
    audio_onset = audio_profile.speech_regions[0].start_ms \
        if audio_profile.speech_regions else 0.0
    audio_end = audio_profile.speech_regions[-1].end_ms \
        if audio_profile.speech_regions else audio_profile.duration_ms

    # Viseme onset / end (first and last non-silence event)
    non_sil = [e for e in events if e.viseme_id != 0]
    viseme_onset = non_sil[0].time_ms if non_sil else 0.0
    viseme_end   = non_sil[-1].time_ms if non_sil else audio_profile.duration_ms

    global_offset = viseme_onset - audio_onset
    return global_offset, audio_onset, viseme_onset, audio_end, viseme_end


# ──────────────────────────────────────────────
# Openness array builder
# ──────────────────────────────────────────────

def visemes_to_openness(
    viseme_events: List[VisemeEventData],
    total_duration_ms: float,
    bin_ms: float = 10.0,
) -> List[float]:
    """
    Convert a list of viseme events into a per-bin openness array.
    Each bin takes the openness value of the viseme active at that time.
    """
    n_bins = max(1, int(math.ceil(total_duration_ms / bin_ms)))
    openness = [0.0] * n_bins

    # Sort by time ascending
    events = sorted(viseme_events, key=lambda e: e.time_ms)

    for i, ev in enumerate(events):
        start_bin = int(ev.time_ms / bin_ms)
        end_bin = int(events[i + 1].time_ms / bin_ms) if i + 1 < len(events) else n_bins
        val = VISEME_OPENNESS.get(ev.viseme_id, 0.0)
        for b in range(max(0, start_bin), min(n_bins, end_bin)):
            openness[b] = val

    return openness


# ──────────────────────────────────────────────
# Drift detection
# ──────────────────────────────────────────────

def _estimate_drift(
    audio_profile: AudioProfile,
    viseme_events: List[VisemeEventData],
) -> float:
    """
    Compare the span of scheduled speech vs the span of detected speech.

    Returns drift_factor = scheduled_speech_ms / actual_speech_ms.
    1.0 = perfect; >1.0 = scheduled is stretched (too slow); <1.0 = compressed.
    """
    # Actual speech span from audio
    if not audio_profile.speech_regions:
        return 1.0
    actual_start = audio_profile.speech_regions[0].start_ms
    actual_end = audio_profile.speech_regions[-1].end_ms
    actual_span = actual_end - actual_start
    if actual_span < 50:
        return 1.0

    # Scheduled speech span: from first non-silence to last non-silence event
    non_sil = [e for e in viseme_events if e.viseme_id != 0]
    if len(non_sil) < 2:
        return 1.0
    sched_start = min(e.time_ms for e in non_sil)
    sched_end = max(e.time_ms for e in non_sil)
    sched_span = sched_end - sched_start
    if sched_span < 50:
        return 1.0

    return sched_span / actual_span


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def evaluate_sync(
    viseme_events: List[VisemeEventData],
    audio_profile: AudioProfile,
    total_duration_ms: Optional[float] = None,
    bin_ms: float = 10.0,
) -> SyncReport:
    """
    Compare a viseme timeline against audio energy to produce a SyncReport.

    Args:
        viseme_events:    List of {time_ms, viseme_id} dicts or VisemeEventData
        audio_profile:    Output of audio_analyzer.analyze_wav()
        total_duration_ms: Override total duration (default: audio_profile.duration_ms)
        bin_ms:           Bin size in ms (default 10)

    Returns:
        SyncReport with global_offset_ms, drift_factor, expected_openness, issues
    """
    if total_duration_ms is None:
        total_duration_ms = audio_profile.duration_ms

    # Coerce dicts to VisemeEventData
    events: List[VisemeEventData] = []
    for e in viseme_events:
        if isinstance(e, dict):
            events.append(VisemeEventData(time_ms=e['time_ms'], viseme_id=e['viseme_id']))
        else:
            events.append(e)

    # Build expected openness signal
    expected_openness = visemes_to_openness(events, total_duration_ms, bin_ms)

    # Build RMS signal at same resolution
    rms_vals = [w.rms for w in audio_profile.rms_windows]

    # Align lengths
    n = min(len(expected_openness), len(rms_vals))
    exp_n = expected_openness[:n]
    rms_n = rms_vals[:n]

    # Normalize for Pearson sanity check only
    exp_norm = _normalize(exp_n)
    rms_norm = _normalize(rms_n)
    pearson_r = _pearson(rms_norm, exp_norm)

    # ── Onset-based offset: far more reliable than cross-correlation ──────────
    # Cross-correlation of mouth-openness vs audio RMS is noisy because
    # sibilants / fricatives have high RMS but small mouth opening. Instead
    # compare when speech STARTS in the audio vs when the first non-silence
    # viseme is scheduled.
    (global_offset_ms,
     audio_onset_ms,
     viseme_onset_ms,
     audio_end_ms,
     viseme_end_ms) = _measure_onset_offset(events, audio_profile)

    # ── Drift factor ──────────────────────────────────────────────────────────
    drift_factor = _estimate_drift(audio_profile, events)

    # Build issues
    issues: List[str] = []

    if abs(global_offset_ms) > 50:
        if global_offset_ms > 0:
            issues.append(
                f"global_offset_ms={global_offset_ms:+.0f} "
                f"(visemes start {global_offset_ms:.0f} ms AFTER audio speech — too late)"
            )
        else:
            issues.append(
                f"global_offset_ms={global_offset_ms:+.0f} "
                f"(visemes start {-global_offset_ms:.0f} ms BEFORE audio speech — too early)"
            )

    if drift_factor > 1.10:
        issues.append(
            f"drift_factor={drift_factor:.3f} "
            f"(viseme timeline {(drift_factor-1)*100:.1f}% longer than actual speech)"
        )
    elif drift_factor < 0.90:
        issues.append(
            f"drift_factor={drift_factor:.3f} "
            f"(viseme timeline {(1-drift_factor)*100:.1f}% shorter than actual speech)"
        )

    return SyncReport(
        global_offset_ms=global_offset_ms,
        drift_factor=drift_factor,
        expected_openness=expected_openness,
        issues=issues,
        pearson_expected_vs_audio=pearson_r,
        audio_onset_ms=audio_onset_ms,
        viseme_onset_ms=viseme_onset_ms,
        audio_end_ms=audio_end_ms,
        viseme_end_ms=viseme_end_ms,
    )


# ──────────────────────────────────────────────
# Full scoring (audio + visemes + animation)
# ──────────────────────────────────────────────

@dataclass
class AnimFrame:
    time_ms: float
    top_viseme_id: int
    top_weight: float
    audio_ms: float = 0.0  # audioSource.time * 1000


@dataclass
class FullSyncResult:
    sync_score: float          # 0–100
    global_offset_ms: float
    drift_factor: float
    animation_lag_ms: float    # median lag of animation behind expected
    peak_attenuation: float    # how much viseme peaks are dampened (0=flat, 1=full)
    issues: List[str]
    next_actions: List[str]


def frames_to_openness(
    frames: List[AnimFrame],
    total_duration_ms: float,
    bin_ms: float = 10.0,
) -> List[float]:
    """Convert animation frame log to per-bin openness array."""
    n_bins = max(1, int(math.ceil(total_duration_ms / bin_ms)))
    openness = [0.0] * n_bins
    if not frames:
        return openness
    for f in frames:
        b = int(f.time_ms / bin_ms)
        if 0 <= b < n_bins:
            openness[b] = f.top_weight
    # Fill gaps with nearest-neighbor
    last = 0.0
    for i in range(n_bins):
        if openness[i] > 0:
            last = openness[i]
        elif last > 0:
            openness[i] = last
    return openness


def compute_full_score(
    audio_profile: AudioProfile,
    viseme_events: List[VisemeEventData],
    anim_frames: List[AnimFrame],
    total_duration_ms: Optional[float] = None,
    bin_ms: float = 10.0,
) -> FullSyncResult:
    """
    Compute a 0–100 sync score comparing audio energy, expected visemes, and
    actual Unity animation.

    Scoring:
    - Base: Pearson correlation of audio RMS vs animation openness (0–100)
    - Penalty: silence during high-energy speech windows (-30 max)
    - Penalty: animation moving during audio silence (-20 max)
    """
    if total_duration_ms is None:
        total_duration_ms = audio_profile.duration_ms

    n_bins = max(1, int(math.ceil(total_duration_ms / bin_ms)))

    rms_full = [w.rms for w in audio_profile.rms_windows]
    # Pad / trim to n_bins
    if len(rms_full) < n_bins:
        rms_full = rms_full + [0.0] * (n_bins - len(rms_full))
    else:
        rms_full = rms_full[:n_bins]

    actual_openness = frames_to_openness(anim_frames, total_duration_ms, bin_ms)

    rms_norm = _normalize(rms_full)
    act_norm = _normalize(actual_openness)

    # Find best lag for alignment (±200 ms)
    lag_bins = _cross_correlate_offset(rms_norm, act_norm, max_lag_bins=20)
    animation_lag_ms = lag_bins * bin_ms

    # Shift animation to align
    act_shifted = [0.0] * n_bins
    for i in range(n_bins):
        j = i + lag_bins
        if 0 <= j < n_bins:
            act_shifted[i] = act_norm[j]

    # Pearson correlation
    corr = _pearson(rms_norm, act_shifted)
    base_score = max(0.0, corr) * 100.0

    # Silence-during-speech penalty
    speech_bins = [i for i, v in enumerate(rms_norm) if v > 0.15]
    if speech_bins:
        silent_during_speech = sum(
            1 for i in speech_bins if act_shifted[i] < 0.05
        ) / len(speech_bins)
    else:
        silent_during_speech = 0.0
    penalty_silence_during_speech = silent_during_speech * 30.0

    # Motion-during-silence penalty
    silence_bins = [i for i, v in enumerate(rms_norm) if v < 0.05]
    if silence_bins:
        moving_during_silence = sum(
            1 for i in silence_bins if act_shifted[i] > 0.2
        ) / len(silence_bins)
    else:
        moving_during_silence = 0.0
    penalty_motion_during_silence = moving_during_silence * 20.0

    score = max(0.0, base_score - penalty_silence_during_speech - penalty_motion_during_silence)

    # Peak attenuation: how much actual peaks are dampened vs expected
    exp_openness = visemes_to_openness(viseme_events, total_duration_ms, bin_ms)
    if exp_openness:
        exp_peak = max(exp_openness)
        act_peak = max(actual_openness) if actual_openness else 0.0
        peak_attenuation = 1.0 - (act_peak / exp_peak) if exp_peak > 1e-9 else 0.0
    else:
        peak_attenuation = 0.0

    # Build issues
    sync_report = evaluate_sync(viseme_events, audio_profile, total_duration_ms, bin_ms)
    issues = list(sync_report.issues)

    if peak_attenuation > 0.3:
        issues.append(
            f"peak attenuation={peak_attenuation:.2f} "
            f"(animation peaks at {(1-peak_attenuation)*100:.0f}% of expected — smoothing too aggressive)"
        )
    if abs(animation_lag_ms) > 40:
        direction = "lags" if animation_lag_ms > 0 else "leads"
        issues.append(
            f"animation {direction} audio by {abs(animation_lag_ms):.0f} ms "
            f"(smoothAdvanceMs may need adjustment)"
        )
    if corr < 0.3:
        issues.append(
            f"low audio-animation correlation ({corr:.2f}) — timing is broadly wrong"
        )

    # Next actions
    next_actions: List[str] = []
    if abs(sync_report.global_offset_ms) > 80:
        adj = -sync_report.global_offset_ms
        next_actions.append(f"Adjust scheduler global_offset_ms by {adj:+.0f} ms")
    if abs(sync_report.drift_factor - 1.0) > 0.05:
        scale = 1.0 / sync_report.drift_factor
        next_actions.append(f"Apply time_scale={scale:.3f} to scheduler")
    if peak_attenuation > 0.3:
        next_actions.append("Reduce smoothTime in AnimClipLipSync to increase peak sharpness")
    if animation_lag_ms > 40:
        next_actions.append(f"Increase smoothAdvanceMs by ~{animation_lag_ms*0.5:.0f} ms")
    if score >= 90:
        next_actions.append("Score ≥ 90 — sync is visually correct")

    return FullSyncResult(
        sync_score=round(score, 1),
        global_offset_ms=sync_report.global_offset_ms,
        drift_factor=sync_report.drift_factor,
        animation_lag_ms=animation_lag_ms,
        peak_attenuation=peak_attenuation,
        issues=issues,
        next_actions=next_actions,
    )
