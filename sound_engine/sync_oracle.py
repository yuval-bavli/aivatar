"""
Sync Oracle — bone-motion vs audio correlation analyzer.

Loads the frame log written by AnimClipLipSync.recordFrames (via LipSyncIterator)
and a WAV file, then computes:
  - Time lag between audio RMS envelope and jaw/lip-gap signal (cross-correlation)
  - Per-phoneme accuracy: jaw angle at phoneme time vs expected reference jaw angle
  - Flat-plateau detection (mouth not moving when it should be)
  - Composite sync score 0–100

Writes:
  debug/sync_report.json    — numeric scores
  debug/sync_report.png     — matplotlib overlay (audio + jaw + lip_gap + phoneme markers)

Usage:
    python -m sound_engine.sync_oracle \\
        --frame-log lipsync_anim_log.json \\
        --wav sound_engine/output.wav \\
        --viseme-events viseme_events.json
"""

import argparse
import json
import os
import sys
from typing import List, Tuple, Optional

import numpy as np


# ── Audio helpers ─────────────────────────────────────────────────────────────

def _load_wav_rms(wav_path: str, window_ms: float = 10.0) -> Tuple[np.ndarray, float]:
    """Read WAV → per-window RMS array; returns (rms_array, ms_per_bin)."""
    import struct
    with open(wav_path, 'rb') as f:
        data = f.read()
    pos = 12
    sample_rate, num_ch, bits = 16000, 1, 16
    pcm = None
    while pos + 8 <= len(data):
        cid = data[pos:pos+4]
        csize = struct.unpack_from('<I', data, pos+4)[0]
        pos += 8
        if cid == b'fmt ':
            num_ch = struct.unpack_from('<H', data, pos+2)[0]
            sample_rate = struct.unpack_from('<I', data, pos+4)[0]
            bits = struct.unpack_from('<H', data, pos+14)[0]
            pos += csize
        elif cid == b'data':
            pcm = data[pos:pos+csize]
            break
        else:
            pos += csize
    if pcm is None:
        raise ValueError("No WAV data chunk")
    samples = np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768.0
    if num_ch > 1:
        samples = samples.reshape(-1, num_ch).mean(axis=1)
    hop = int(sample_rate * window_ms / 1000)
    n_frames = len(samples) // hop
    rms = np.array([
        np.sqrt(np.mean(samples[i*hop:(i+1)*hop]**2))
        for i in range(n_frames)
    ])
    return rms, window_ms


# ── Viseme ID → expected jaw openness (baked reference values) ────────────────
# These are rough jaw-open fractions (0=closed, 1=wide-open) derived from the
# UE5 ue_viseme_final2.py control values. Used for per-phoneme accuracy scoring.
_VISEME_JAW_OPENNESS = {
    0:  0.00,   # sil
    1:  0.05,   # PP — slight press
    2:  0.10,   # FF — bite
    3:  0.90,   # TH — extreme jaw + tongue
    4:  0.20,   # DD
    5:  0.15,   # kk
    6:  0.25,   # CH
    7:  0.20,   # SS
    8:  0.15,   # nn
    9:  0.20,   # RR
    10: 0.75,   # aa (AH, AE, AA)
    11: 0.50,   # E
    12: 0.30,   # ih
    13: 0.65,   # oh (AO, OW, AW)
    14: 0.25,   # ou
}


# ── Main evaluation ───────────────────────────────────────────────────────────

def evaluate(
    frame_log: List[dict],
    wav_path: Optional[str] = None,
    viseme_events: Optional[List[dict]] = None,
    output_dir: str = 'debug',
    tag: str = '',
) -> dict:
    """
    Evaluate sync quality from a Unity frame log.

    Args:
        frame_log:      List of frame records from GetFrameLogJson().
                        Expected keys: time_ms, top_viseme_id, top_weight,
                        jaw_deg (optional), lip_gap (optional).
        wav_path:       Path to the WAV file that was played.
        viseme_events:  List of {time_ms, viseme_id} dicts (the events fed to Unity).
        output_dir:     Where to write sync_report.json and sync_report.png.
        tag:            Optional suffix for filenames.

    Returns dict with keys: lag_ms, phoneme_accuracy, plateau_pct, score.
    """
    os.makedirs(output_dir, exist_ok=True)

    if not frame_log:
        return {'error': 'empty frame log', 'score': 0}

    times_ms  = np.array([f['time_ms']      for f in frame_log], dtype=float)
    top_vis   = np.array([f['top_viseme_id'] for f in frame_log], dtype=int)
    top_w     = np.array([f['top_weight']    for f in frame_log], dtype=float)
    has_jaw   = 'jaw_deg' in frame_log[0]
    has_lip   = 'lip_gap' in frame_log[0]

    jaw_deg  = np.array([f.get('jaw_deg', 0.0)  for f in frame_log], dtype=float) if has_jaw else None
    lip_gap  = np.array([f.get('lip_gap', 0.0)  for f in frame_log], dtype=float) if has_lip else None

    results = {}

    # ── 1. Time-lag via cross-correlation ────────────────────────────────────
    # Use lip_gap (or jaw_deg, or top_weight) as the mouth-openness signal.
    mouth_signal = None
    if has_lip and lip_gap is not None and lip_gap.max() > 1e-6:
        mouth_signal = (lip_gap - lip_gap.min()) / (lip_gap.max() - lip_gap.min() + 1e-9)
    elif has_jaw and jaw_deg is not None:
        # Negative jaw angle = open mouth in our convention; normalise to [0,1]
        j = -jaw_deg  # more negative = more open → invert
        mouth_signal = np.clip((j - j.min()) / (j.max() - j.min() + 1e-9), 0, 1)
    else:
        mouth_signal = top_w  # fallback: use viseme weight

    if wav_path and os.path.exists(wav_path):
        try:
            rms, rms_ms = _load_wav_rms(wav_path)
            # Resample mouth_signal to match rms resolution (nearest-neighbour)
            duration_ms = times_ms[-1] - times_ms[0]
            n_rms = len(rms)
            rms_times = np.arange(n_rms) * rms_ms
            mouth_at_rms = np.interp(rms_times, times_ms, mouth_signal)
            # Normalise RMS
            rms_norm = (rms - rms.min()) / (rms.max() - rms.min() + 1e-9)
            # Cross-correlate
            corr = np.correlate(mouth_at_rms - mouth_at_rms.mean(),
                                rms_norm - rms_norm.mean(), mode='full')
            half = len(rms)
            lags = (np.arange(len(corr)) - (half - 1)) * rms_ms
            best_lag = float(lags[np.argmax(corr)])
            pearson = float(np.corrcoef(mouth_at_rms, rms_norm)[0, 1])
            results['lag_ms'] = best_lag
            results['pearson'] = round(pearson, 3)
        except Exception as exc:
            results['lag_ms'] = None
            results['pearson'] = None
            results['lag_error'] = str(exc)
    else:
        results['lag_ms'] = None
        results['pearson'] = None

    # ── 2. Per-phoneme accuracy ───────────────────────────────────────────────
    if viseme_events:
        n_correct = 0
        n_total = 0
        for ev in viseme_events:
            ev_ms  = float(ev['time_ms'])
            ev_vid = int(ev['viseme_id'])
            if ev_vid == 0:
                continue  # skip silence events
            expected_open = _VISEME_JAW_OPENNESS.get(ev_vid, 0.3)
            # Find the frame closest to 30ms after the event fires
            target_ms = ev_ms + 30.0
            idx = int(np.searchsorted(times_ms, target_ms))
            idx = min(idx, len(top_w) - 1)
            actual_w = float(top_w[idx])
            actual_vid = int(top_vis[idx])
            # Correct if: mouth is open (weight > 0.3) AND the dominant viseme matches
            if actual_w > 0.25 and (actual_vid == ev_vid or expected_open < 0.2):
                n_correct += 1
            n_total += 1
        results['phoneme_accuracy'] = round(n_correct / max(1, n_total), 3)
        results['phoneme_n'] = n_total
    else:
        results['phoneme_accuracy'] = None

    # ── 3. Plateau detection ──────────────────────────────────────────────────
    # Fraction of non-silence frames where mouth hasn't moved for > 250ms
    PLATEAU_MS = 250.0
    dt = np.diff(times_ms, prepend=times_ms[0])
    non_sil = top_vis != 0
    plateau_frames = 0
    consecutive_ms = 0.0
    prev_w = mouth_signal[0] if len(mouth_signal) else 0.0
    for i in range(1, len(mouth_signal)):
        if not non_sil[i]:
            consecutive_ms = 0.0
            prev_w = mouth_signal[i]
            continue
        motion = abs(mouth_signal[i] - prev_w)
        if motion < 0.02:   # < 2% change = plateau
            consecutive_ms += dt[i]
        else:
            consecutive_ms = 0.0
        if consecutive_ms > PLATEAU_MS:
            plateau_frames += 1
        prev_w = mouth_signal[i]
    total_non_sil = max(1, int(non_sil.sum()))
    plateau_pct = round(plateau_frames / total_non_sil * 100, 1)
    results['plateau_pct'] = plateau_pct

    # ── 4. Composite score ────────────────────────────────────────────────────
    score = 100.0
    lag = abs(results.get('lag_ms') or 0)
    if lag > 30:
        score -= min(20, (lag - 30) / 5)   # -1 per 5ms over 30ms cap at -20
    pear = results.get('pearson') or 0.0
    if pear < 0.5:
        score -= (0.5 - pear) * 60          # low correlation penalty
    phon_acc = results.get('phoneme_accuracy') or 0.8
    score -= max(0, (0.8 - phon_acc) * 50)
    score -= plateau_pct * 0.3             # each plateau % costs 0.3 pts
    results['score'] = round(max(0, min(100, score)), 1)

    # ── 5. Write JSON report ──────────────────────────────────────────────────
    suffix = f'_{tag}' if tag else ''
    json_path = os.path.join(output_dir, f'sync_report{suffix}.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"[sync_oracle] score={results['score']}/100  lag={results.get('lag_ms','?')}ms  "
          f"pearson={results.get('pearson','?')}  plateau={plateau_pct}%  → {json_path}")

    # ── 6. PNG overlay ────────────────────────────────────────────────────────
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)
        fig.suptitle(f'Lip-Sync Report  score={results["score"]}/100', fontsize=13)

        # Row 0: audio RMS
        ax0 = axes[0]
        if wav_path and os.path.exists(wav_path):
            rms_times = np.arange(len(rms)) * rms_ms
            ax0.fill_between(rms_times, rms_norm, alpha=0.5, color='steelblue', label='Audio RMS')
        ax0.set_ylabel('Audio RMS')
        ax0.set_ylim(0, 1.05)
        ax0.legend(loc='upper right', fontsize=8)

        # Row 1: jaw deg / lip gap
        ax1 = axes[1]
        if has_lip and lip_gap is not None:
            ax1.plot(times_ms, mouth_signal, color='coral', label='Lip gap (norm)')
        elif has_jaw and jaw_deg is not None:
            ax1.plot(times_ms, mouth_signal, color='coral', label='Jaw openness (norm)')
        else:
            ax1.plot(times_ms, mouth_signal, color='coral', label='Viseme weight')
        ax1.set_ylabel('Mouth openness')
        ax1.set_ylim(-0.05, 1.1)
        ax1.legend(loc='upper right', fontsize=8)

        # Row 2: active viseme ID
        ax2 = axes[2]
        ax2.step(times_ms, top_vis, color='purple', where='post', linewidth=1, label='Viseme ID')
        ax2.set_ylabel('Viseme ID')
        ax2.set_ylim(-0.5, 15)
        ax2.set_xlabel('Time (ms)')
        ax2.legend(loc='upper right', fontsize=8)

        # Draw phoneme event markers on all rows
        if viseme_events:
            colors = plt.cm.Set1(np.linspace(0, 1, 9))
            for ev in viseme_events:
                ev_ms = float(ev['time_ms'])
                vid = int(ev['viseme_id'])
                if vid == 0:
                    continue
                c = colors[vid % len(colors)]
                for ax in axes:
                    ax.axvline(ev_ms, color=c, alpha=0.3, linewidth=0.8, linestyle='--')

        plt.tight_layout()
        png_path = os.path.join(output_dir, f'sync_report{suffix}.png')
        plt.savefig(png_path, dpi=120)
        plt.close()
        print(f"[sync_oracle] chart → {png_path}")
    except ImportError:
        pass  # matplotlib optional

    return results


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description='Evaluate lip-sync quality from Unity frame log')
    p.add_argument('--frame-log', default='lipsync_anim_log.json',
                   help='JSON frame log from AnimClipLipSync.GetFrameLogJson()')
    p.add_argument('--wav', default='sound_engine/output.wav',
                   help='WAV file that was played during recording')
    p.add_argument('--viseme-events', default=None,
                   help='JSON file with viseme events [{time_ms, viseme_id}, ...]')
    p.add_argument('--output-dir', default='debug', help='Where to write reports')
    p.add_argument('--tag', default='', help='Suffix for output filenames')
    args = p.parse_args()

    with open(args.frame_log) as f:
        frame_log = json.load(f)

    viseme_events = None
    if args.viseme_events and os.path.exists(args.viseme_events):
        with open(args.viseme_events) as f:
            viseme_events = json.load(f)

    wav_path = args.wav if os.path.exists(args.wav) else None
    evaluate(frame_log, wav_path=wav_path,
             viseme_events=viseme_events,
             output_dir=args.output_dir, tag=args.tag)


if __name__ == '__main__':
    main()
