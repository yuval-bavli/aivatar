"""
Pixel Oracle — face-landmark-based lip distance vs audio correlation.

Loads the PNG frame sequence written by LipSyncFrameRecorder.cs and uses
mediapipe face mesh to extract lip distance per frame, then:
  1. Correlates lip_distance_pixels with audio RMS → proves sync at pixel level
  2. Correlates lip_distance_pixels with bone-motion lip_gap (from frame log) →
     proves the render/rig faithfully follows the bone drive

Writes:
  debug/sync_pixel_report.json   — numeric scores
  debug/sync_pixel_report.png    — overlay: audio waveform + lip distance + phoneme bars

Usage:
    python -m sound_engine.sync_pixel_oracle \\
        --video-dir debug/lipsync_video \\
        --wav sound_engine/output.wav \\
        --frame-log lipsync_anim_log.json \\
        --output-dir debug
"""

import argparse
import json
import os
from typing import Optional, Tuple

import numpy as np


def _wav_rms(wav_path: str, window_ms: float = 10.0) -> Tuple[np.ndarray, float]:
    """Return (rms_array, ms_per_bin)."""
    import struct
    with open(wav_path, 'rb') as f:
        data = f.read()
    pos = 12
    sr, ch, bits = 16000, 1, 16
    pcm = None
    while pos + 8 <= len(data):
        cid = data[pos:pos+4]
        csize = struct.unpack_from('<I', data, pos+4)[0]
        pos += 8
        if cid == b'fmt ':
            ch = struct.unpack_from('<H', data, pos+2)[0]
            sr = struct.unpack_from('<I', data, pos+4)[0]
            bits = struct.unpack_from('<H', data, pos+14)[0]
            pos += csize
        elif cid == b'data':
            pcm = data[pos:pos+csize]
            break
        else:
            pos += csize
    samples = np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768.0
    if ch > 1:
        samples = samples.reshape(-1, ch).mean(axis=1)
    hop = int(sr * window_ms / 1000)
    n = len(samples) // hop
    rms = np.array([np.sqrt(np.mean(samples[i*hop:(i+1)*hop]**2)) for i in range(n)])
    return rms, window_ms


def analyze(
    video_dir: str,
    wav_path: Optional[str] = None,
    frame_log_path: Optional[str] = None,
    output_dir: str = 'debug',
) -> dict:
    """Run the pixel oracle. Returns a results dict."""
    os.makedirs(output_dir, exist_ok=True)

    # Load frame manifest
    manifest_path = os.path.join(video_dir, 'frame_manifest.json')
    if not os.path.exists(manifest_path):
        return {'error': f'manifest not found: {manifest_path}', 'score': 0}

    with open(manifest_path) as f:
        manifest = json.load(f)
    if not manifest:
        return {'error': 'empty manifest', 'score': 0}

    frame_times = np.array([e['elapsed_ms'] for e in manifest], dtype=float)

    # Extract lip distance per frame using mediapipe
    try:
        import mediapipe as mp
        from PIL import Image
    except ImportError as e:
        return {'error': f'mediapipe/PIL not installed: {e}', 'score': 0}

    mp_face = mp.solutions.face_mesh
    lip_distances = []

    # Mediapipe lip landmarks (upper: 13, lower: 14 in the 468-landmark set)
    UPPER_LIP = 13
    LOWER_LIP = 14

    with mp_face.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.3,
    ) as face_mesh:
        for entry in manifest:
            fpath = os.path.join(video_dir, entry['file'])
            if not os.path.exists(fpath):
                lip_distances.append(0.0)
                continue
            img = np.array(Image.open(fpath).convert('RGB'))
            result = face_mesh.process(img)
            if result.multi_face_landmarks:
                lm = result.multi_face_landmarks[0].landmark
                upper_y = lm[UPPER_LIP].y
                lower_y = lm[LOWER_LIP].y
                dist = abs(lower_y - upper_y) * img.shape[0]   # pixels
                lip_distances.append(dist)
            else:
                lip_distances.append(np.nan)

    lip_px = np.array(lip_distances, dtype=float)
    # Fill NaN with median
    med = np.nanmedian(lip_px) if not np.all(np.isnan(lip_px)) else 0.0
    lip_px = np.where(np.isnan(lip_px), med, lip_px)

    results = {}
    lip_norm = (lip_px - lip_px.min()) / (lip_px.max() - lip_px.min() + 1e-9)

    # ── 1. Pixel vs audio RMS correlation ─────────────────────────────────────
    if wav_path and os.path.exists(wav_path):
        rms, rms_ms = _wav_rms(wav_path)
        rms_times = np.arange(len(rms)) * rms_ms
        # Resample lip to rms grid
        lip_at_rms = np.interp(rms_times, frame_times, lip_norm)
        rms_norm = (rms - rms.min()) / (rms.max() - rms.min() + 1e-9)
        corr = np.correlate(lip_at_rms - lip_at_rms.mean(),
                            rms_norm - rms_norm.mean(), mode='full')
        lags = (np.arange(len(corr)) - (len(rms) - 1)) * rms_ms
        best_lag = float(lags[np.argmax(corr)])
        pearson = float(np.corrcoef(lip_at_rms, rms_norm)[0, 1])
        results['pixel_audio_lag_ms'] = best_lag
        results['pixel_audio_pearson'] = round(pearson, 3)
    else:
        rms_times = None
        results['pixel_audio_lag_ms'] = None
        results['pixel_audio_pearson'] = None

    # ── 2. Pixel vs bone lip_gap correlation ──────────────────────────────────
    if frame_log_path and os.path.exists(frame_log_path):
        with open(frame_log_path) as f:
            frame_log = json.load(f)
        if frame_log and 'lip_gap' in frame_log[0]:
            bone_times = np.array([e['time_ms'] for e in frame_log], dtype=float)
            bone_lip   = np.array([e['lip_gap']  for e in frame_log], dtype=float)
            bone_norm  = (bone_lip - bone_lip.min()) / (bone_lip.max() - bone_lip.min() + 1e-9)
            # Resample bone to pixel frame times
            bone_at_frames = np.interp(frame_times, bone_times, bone_norm)
            pear_bone = float(np.corrcoef(lip_norm, bone_at_frames)[0, 1])
            results['pixel_bone_pearson'] = round(pear_bone, 3)
        else:
            results['pixel_bone_pearson'] = None
    else:
        results['pixel_bone_pearson'] = None

    # ── 3. Composite pixel score ───────────────────────────────────────────────
    score = 100.0
    pa = results.get('pixel_audio_pearson') or 0.0
    pb = results.get('pixel_bone_pearson') or 1.0
    if pa < 0.5:
        score -= (0.5 - pa) * 80
    if pb < 0.85:
        score -= (0.85 - pb) * 60
    lag = abs(results.get('pixel_audio_lag_ms') or 0)
    if lag > 50:
        score -= min(20, (lag - 50) / 5)
    results['pixel_score'] = round(max(0, min(100, score)), 1)

    # ── 4. JSON report ─────────────────────────────────────────────────────────
    json_path = os.path.join(output_dir, 'sync_pixel_report.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"[pixel_oracle] pixel_score={results['pixel_score']}/100  "
          f"audio_pearson={results.get('pixel_audio_pearson','?')}  "
          f"bone_pearson={results.get('pixel_bone_pearson','?')} → {json_path}")

    # ── 5. PNG overlay ─────────────────────────────────────────────────────────
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=True)
        fig.suptitle(f'Pixel Lip-Sync Oracle  pixel_score={results["pixel_score"]}/100', fontsize=13)

        ax0 = axes[0]
        if rms_times is not None:
            ax0.fill_between(rms_times, rms_norm, alpha=0.4, color='steelblue', label='Audio RMS')
        ax0.plot(frame_times, lip_norm, color='coral', linewidth=1.5, label='Pixel lip distance (norm)')
        ax0.set_ylabel('Signal (norm)')
        ax0.set_ylim(-0.05, 1.1)
        ax0.legend(fontsize=8, loc='upper right')

        ax1 = axes[1]
        if frame_log_path and os.path.exists(frame_log_path) and 'lip_gap' in frame_log[0]:
            ax1.plot(bone_times, bone_norm, color='purple', linewidth=1, label='Bone lip_gap (norm)')
            ax1.plot(frame_times, lip_norm, color='coral', linewidth=1, alpha=0.7,
                     label='Pixel lip distance (norm)')
            ax1.set_ylabel('Lip signal')
            ax1.legend(fontsize=8, loc='upper right')

        ax1.set_xlabel('Time (ms)')
        plt.tight_layout()
        png_path = os.path.join(output_dir, 'sync_pixel_report.png')
        plt.savefig(png_path, dpi=120)
        plt.close()
        print(f"[pixel_oracle] chart → {png_path}")
    except ImportError:
        pass

    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--video-dir', default='debug/lipsync_video')
    p.add_argument('--wav', default='sound_engine/output.wav')
    p.add_argument('--frame-log', default='lipsync_anim_log.json')
    p.add_argument('--output-dir', default='debug')
    args = p.parse_args()
    analyze(args.video_dir, args.wav, args.frame_log, args.output_dir)


if __name__ == '__main__':
    main()
