"""
Mutable parameter store for the lip sync optimizer.

Persists to lipsync_params.json at the repo root.
Loaded by the scheduler and server on every request; applied to Unity
before each play cycle.

Keys:
  global_offset_ms  float   Shift all viseme timestamps by this amount (ms)
  time_scale        float   Multiply all scheduled durations by this factor
  vowel_weight      float   Enhanced-mode weight for vowel phonemes
  consonant_weight  float   Enhanced-mode weight for consonant phonemes
  smoothAdvanceMs   float   AnimClipLipSync: forward-shift to compensate SmoothDamp
  smoothTime        float   AnimClipLipSync: SmoothDamp settling time
  crossfadeEase     float   AnimClipLipSync: easing exponent for crossfade bias
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

# Repo root is one directory above this file's package
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_PATH = os.path.join(_REPO_ROOT, 'lipsync_params.json')


@dataclass
class LipSyncParams:
    # Scheduler params
    global_offset_ms: float = 0.0
    time_scale: float = 1.0
    vowel_weight: float = 1.5
    consonant_weight: float = 0.6

    # Unity AnimClipLipSync params
    smoothAdvanceMs: float = 40.0
    smoothTime: float = 0.03
    crossfadeEase: float = 1.5


def load(path: str = DEFAULT_PATH) -> LipSyncParams:
    """Load params from JSON file; returns defaults if file missing."""
    if not os.path.exists(path):
        return LipSyncParams()
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    p = LipSyncParams()
    for key, val in data.items():
        if hasattr(p, key):
            setattr(p, key, float(val))
    return p


def save(params: LipSyncParams, path: str = DEFAULT_PATH) -> None:
    """Save params to JSON file (creates or overwrites)."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(asdict(params), f, indent=2)


def apply_fixes(
    params: LipSyncParams,
    global_offset_ms: Optional[float] = None,
    drift_factor: Optional[float] = None,
    peak_attenuation: Optional[float] = None,
    animation_lag_ms: Optional[float] = None,
    pearson_r: Optional[float] = None,
    damping: float = 0.5,
) -> LipSyncParams:
    """
    Return a new LipSyncParams with deterministic fixes applied.

    Uses `damping` (default 0.5) to apply only half the detected error each
    iteration — prevents oscillation and runaway accumulation.

    Bounds:
    - global_offset_ms: [-800, 800] ms
    - time_scale:        [0.5, 2.0]
    - smoothAdvanceMs:   [0, 200]
    - smoothTime:        [0.01, 0.2]
    - vowel_weight:      [1.0, 3.0]

    Sign conventions:
    - global_offset_ms > 0: visemes start AFTER audio (too late)
      Fix: subtract offset from scheduler param → visemes move earlier
      scheduler applies: ms = ms + global_offset_ms_param
      so to shift earlier: global_offset_ms_param -= measured_offset * damping

    - drift_factor > 1: timeline stretched (too slow)
      Fix: compress by multiplying time_scale by (1/drift_factor)
    """
    import dataclasses
    p = dataclasses.replace(params)  # shallow copy

    # 1. Global offset correction (damped)
    if global_offset_ms is not None and abs(global_offset_ms) > 50:
        correction = -global_offset_ms * damping  # flip sign: late → shift earlier
        p.global_offset_ms = round(
            max(-800.0, min(800.0, p.global_offset_ms + correction)), 1)

    # 2. Drift correction (damped multiplicative)
    if drift_factor is not None and abs(drift_factor - 1.0) > 0.05:
        # Partial correction toward 1.0: blend current drift with 1.0 by damping
        target_scale = 1.0 / drift_factor
        partial_scale = 1.0 + (target_scale - 1.0) * damping
        new_scale = p.time_scale * partial_scale
        p.time_scale = round(max(0.5, min(2.0, new_scale)), 4)

    # 3. Over-smoothing — reduce smoothTime (floor at 0.01)
    if peak_attenuation is not None and peak_attenuation > 0.3:
        p.smoothTime = round(max(0.01, min(0.2, p.smoothTime * 0.7)), 4)

    # 4. Animation lag — increase smoothAdvanceMs
    if animation_lag_ms is not None and animation_lag_ms > 40:
        increase = animation_lag_ms * damping
        p.smoothAdvanceMs = round(min(200.0, p.smoothAdvanceMs + increase), 1)

    # 5. Very low correlation — boost vowel presence
    if pearson_r is not None and pearson_r < 0.4:
        p.vowel_weight = round(min(3.0, p.vowel_weight * 1.15), 3)

    return p
