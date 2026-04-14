"""
Automated lip sync optimization loop.

Usage:
    # From repo root (server must be running):
    .venv/Scripts/python -m sound_engine.lipsync_iterator
    .venv/Scripts/python -m sound_engine.lipsync_iterator "Hello world"
    .venv/Scripts/python -m sound_engine.lipsync_iterator --iterations 5

The loop:
  1. Synthesize test phrase via the sound_engine server
  2. Analyze WAV energy → ground-truth timing
  3. Compare expected visemes vs audio → detect offset + drift
  4. Write lipsync_test_input.json for Unity
  5. Trigger Unity play cycle via agent bridge
  6. Read lipsync_anim_log.json → actual animation frames
  7. Compute full sync score (0–100)
  8. If score < 90: apply parameter fixes and repeat
  9. Print final report JSON

Convergence:
  score ≥ 90        → done
  score 70–89       → apply fixes, continue
  score < 70 iter ≥ 3 → also adjust phoneme weights
  max 8 iterations  → NEEDS_MANUAL_REVIEW if not converged
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error

# ── Path setup ────────────────────────────────────────────────────────────────

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, '..'))
_UNITY_PROJECT = os.path.join(_REPO_ROOT, 'unity', 'aivatar')

sys.path.insert(0, _REPO_ROOT)

from sound_engine.audio_analyzer import analyze_wav
from sound_engine.sync_evaluator import (
    evaluate_sync, compute_full_score,
    VisemeEventData, AnimFrame,
)
from sound_engine import param_config

# ── Constants ─────────────────────────────────────────────────────────────────

SERVER_URL = 'http://127.0.0.1:5123/speak'
TEST_PHRASES = [
    "Hello, how are you doing today?",
    "The quick brown fox jumps over the lazy dog.",
    "Thank you very much.",
]
# Default phrase used when no text is provided.
# Using a SINGLE phrase for all iterations is essential for convergence —
# rotating phrases means each iteration measures a different audio, so
# corrections for phrase 1 corrupt phrase 2.
DEFAULT_PHRASE = TEST_PHRASES[0]
MAX_ITERATIONS = 8
SCORE_TARGET = 90.0
AGENT_REQUEST_FILE = os.path.join(_UNITY_PROJECT, 'agent_request.txt')
AGENT_RESULT_FILE  = os.path.join(_UNITY_PROJECT, 'agent_result.txt')
TEST_INPUT_FILE    = os.path.join(_UNITY_PROJECT, 'lipsync_test_input.json')
ANIM_LOG_FILE      = os.path.join(_UNITY_PROJECT, 'lipsync_anim_log.json')
PARAMS_FILE        = os.path.join(_REPO_ROOT, 'lipsync_params.json')


# ── Server communication ───────────────────────────────────────────────────────

def speak(text: str) -> dict:
    """POST to the sound_engine server and return the response dict."""
    payload = json.dumps({'text': text}).encode('utf-8')
    req = urllib.request.Request(
        SERVER_URL,
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


# ── Unity bridge ──────────────────────────────────────────────────────────────

def trigger_unity_iteration() -> str:
    """Write execute command to agent bridge; return quickly."""
    # Remove stale result file
    if os.path.exists(AGENT_RESULT_FILE):
        os.remove(AGENT_RESULT_FILE)

    with open(AGENT_REQUEST_FILE, 'w') as f:
        f.write('execute LipSyncIterator.RunIteration')

    return 'triggered'


def wait_for_anim_log(timeout_s: float = 30.0, poll_s: float = 0.5) -> list:
    """
    Poll until lipsync_anim_log.json appears and is non-empty.
    Returns list of frame dicts, or empty list on timeout.
    """
    deadline = time.time() + timeout_s
    # First wait for agent_result.txt to confirm Unity finished
    while time.time() < deadline:
        if os.path.exists(AGENT_RESULT_FILE):
            result = open(AGENT_RESULT_FILE).read().strip()
            if result.startswith('OK') or result.startswith('STARTED'):
                break
        time.sleep(poll_s)

    # Then wait for anim log
    while time.time() < deadline:
        if os.path.exists(ANIM_LOG_FILE):
            try:
                data = json.loads(open(ANIM_LOG_FILE).read())
                if isinstance(data, list) and len(data) > 0:
                    return data
            except json.JSONDecodeError:
                pass
        time.sleep(poll_s)

    print(f"  [warn] Timed out waiting for lipsync_anim_log.json after {timeout_s}s", flush=True)
    return []


# ── Data conversion ────────────────────────────────────────────────────────────

def to_viseme_events(raw: list) -> list:
    """Convert server response viseme_events to VisemeEventData list."""
    return [VisemeEventData(time_ms=e['time_ms'], viseme_id=e['viseme_id']) for e in raw]


def to_anim_frames(raw: list) -> list:
    """Convert lipsync_anim_log.json records to AnimFrame list."""
    frames = []
    for r in raw:
        frames.append(AnimFrame(
            time_ms=float(r.get('time_ms', 0)),
            top_viseme_id=int(r.get('top_viseme_id', 0)),
            top_weight=float(r.get('top_weight', 0)),
            audio_ms=float(r.get('audio_ms', 0)),
        ))
    return frames


# ── Test input file ────────────────────────────────────────────────────────────

def write_test_input(server_response: dict) -> None:
    """Write lipsync_test_input.json for Unity LipSyncIterator to consume."""
    payload = {
        'audio_base64': server_response['audio_base64'],
        'sample_rate': server_response.get('sample_rate', 22050),
        'duration_ms': server_response['duration_ms'],
        'viseme_events': server_response['viseme_events'],
    }
    with open(TEST_INPUT_FILE, 'w') as f:
        json.dump(payload, f)


# ── Per-iteration report ───────────────────────────────────────────────────────

def print_iteration_report(iteration: int, phrase: str, result, fixes_applied: dict):
    report = {
        'iteration': iteration,
        'phrase': phrase,
        'sync_score': result.sync_score,
        'global_offset_ms': result.global_offset_ms,
        'drift_factor': result.drift_factor,
        'animation_lag_ms': result.animation_lag_ms,
        'peak_attenuation': result.peak_attenuation,
        'issues': result.issues,
        'fixes_applied': fixes_applied,
        'next_actions': result.next_actions,
    }
    print(json.dumps(report, indent=2), flush=True)


# ── Main loop ─────────────────────────────────────────────────────────────────

def run(
    text: str = None,
    iterations: int = MAX_ITERATIONS,
    no_unity: bool = False,
) -> dict:
    """
    Run the optimization loop.

    Args:
        text:        Override the default test phrase rotation
        iterations:  Maximum number of iterations
        no_unity:    Skip Unity playback (analyze audio + visemes only)

    Returns:
        Final report dict
    """
    print("=" * 60)
    print("Lip Sync Optimizer — starting")
    print(f"  server:     {SERVER_URL}")
    print(f"  iterations: {iterations}")
    print(f"  target:     score >= {SCORE_TARGET}")
    print("=" * 60, flush=True)

    params = param_config.load(PARAMS_FILE)
    best_score = 0.0
    history = []

    # Fix one phrase for all iterations so corrections are comparable
    fixed_phrase = text if text else DEFAULT_PHRASE

    for i in range(1, iterations + 1):
        phrase = fixed_phrase

        print(f"\n--- Iteration {i}/{iterations}: \"{phrase}\" ---", flush=True)

        # ── Step 1: Synthesize ───────────────────────────────────────────────
        print("  [1] Speaking...", flush=True)
        try:
            response = speak(phrase)
        except Exception as ex:
            print(f"  ERROR: Server request failed: {ex}")
            print("  Make sure sound_engine/server.py is running.")
            break

        wav_b64 = response['audio_base64']
        wav_bytes = base64.b64decode(wav_b64)
        duration_ms = response['duration_ms']
        raw_visemes = response['viseme_events']
        viseme_events = to_viseme_events(raw_visemes)

        print(f"  audio={duration_ms:.0f}ms  visemes={len(viseme_events)}", flush=True)

        # ── Step 2: Analyze audio ────────────────────────────────────────────
        print("  [2] Analyzing audio...", flush=True)
        audio_profile = analyze_wav(wav_bytes)
        speech_span = (
            f"{audio_profile.speech_regions[0].start_ms:.0f}–"
            f"{audio_profile.speech_regions[-1].end_ms:.0f}ms"
        ) if audio_profile.speech_regions else "none"
        print(f"  speech={speech_span}  peaks={len(audio_profile.peaks)}", flush=True)

        # ── Step 3: Evaluate sync ────────────────────────────────────────────
        print("  [3] Evaluating sync...", flush=True)
        sync_report = evaluate_sync(viseme_events, audio_profile, duration_ms)
        print(f"  audio:  speech {sync_report.audio_onset_ms:.0f}–{sync_report.audio_end_ms:.0f} ms", flush=True)
        print(f"  viseme: active {sync_report.viseme_onset_ms:.0f}–{sync_report.viseme_end_ms:.0f} ms", flush=True)
        print(f"  offset={sync_report.global_offset_ms:+.0f}ms  "
              f"drift={sync_report.drift_factor:.3f}  "
              f"pearson={sync_report.pearson_expected_vs_audio:.2f}", flush=True)

        # ── Step 4: Unity playback + animation capture ───────────────────────
        anim_frames = []
        if not no_unity:
            print("  [4] Writing test input for Unity...", flush=True)
            write_test_input(response)

            print("  [5] Triggering Unity play cycle...", flush=True)
            trigger_unity_iteration()

            print("  [6] Waiting for animation log...", flush=True)
            raw_frames = wait_for_anim_log(timeout_s=35.0)
            anim_frames = to_anim_frames(raw_frames)
            print(f"  captured {len(anim_frames)} frames", flush=True)
        else:
            print("  [4–6] Skipped (no-unity mode)", flush=True)

        # ── Step 6: Compute full score ───────────────────────────────────────
        print("  [7] Computing score...", flush=True)
        if anim_frames:
            full_result = compute_full_score(
                audio_profile, viseme_events, anim_frames, duration_ms)
        else:
            # No Unity data — score based on expected-vs-audio only
            from sound_engine.sync_evaluator import FullSyncResult
            base_score = max(0.0, sync_report.pearson_expected_vs_audio) * 70.0
            full_result = FullSyncResult(
                sync_score=round(base_score, 1),
                global_offset_ms=sync_report.global_offset_ms,
                drift_factor=sync_report.drift_factor,
                animation_lag_ms=0.0,
                peak_attenuation=0.0,
                issues=sync_report.issues,
                next_actions=sync_report.issues,
            )

        score = full_result.sync_score
        best_score = max(best_score, score)
        history.append({'iteration': i, 'score': score, 'phrase': phrase})

        # ── Step 7: Apply fixes ──────────────────────────────────────────────
        fixes_applied = {}
        if score < SCORE_TARGET:
            new_params = param_config.apply_fixes(
                params,
                global_offset_ms=full_result.global_offset_ms,
                drift_factor=full_result.drift_factor,
                peak_attenuation=full_result.peak_attenuation if anim_frames else None,
                animation_lag_ms=full_result.animation_lag_ms if anim_frames else None,
                pearson_r=sync_report.pearson_expected_vs_audio if score < 70 and i >= 3 else None,
            )
            # Record what changed
            for key in ('global_offset_ms', 'time_scale', 'vowel_weight',
                        'smoothAdvanceMs', 'smoothTime', 'crossfadeEase'):
                old_val = getattr(params, key)
                new_val = getattr(new_params, key)
                if abs(old_val - new_val) > 0.0001:
                    fixes_applied[key] = {'before': old_val, 'after': new_val}

            if fixes_applied:
                param_config.save(new_params, PARAMS_FILE)
                params = new_params
                print(f"  fixes applied: {list(fixes_applied.keys())}", flush=True)
            else:
                print("  no parameter changes needed", flush=True)
        else:
            print(f"  score={score:.1f} ≥ {SCORE_TARGET} — target reached!", flush=True)

        print_iteration_report(i, phrase, full_result, fixes_applied)

        if score >= SCORE_TARGET:
            break

    # ── Final report ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    converged = best_score >= SCORE_TARGET
    status = "CONVERGED" if converged else "NEEDS_MANUAL_REVIEW"

    final = {
        'status': status,
        'best_score': best_score,
        'iterations_run': len(history),
        'history': history,
        'final_params': {
            'global_offset_ms': params.global_offset_ms,
            'time_scale': params.time_scale,
            'vowel_weight': params.vowel_weight,
            'smoothAdvanceMs': params.smoothAdvanceMs,
            'smoothTime': params.smoothTime,
            'crossfadeEase': params.crossfadeEase,
        },
    }
    if not converged:
        final['top_issues'] = []
        # Collect unique issues from last iteration
        if history:
            pass  # Issues printed per-iteration above

    print(json.dumps(final, indent=2), flush=True)
    print("=" * 60)
    return final


# ── CLI entry point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Automated lip sync optimization loop')
    parser.add_argument(
        'text', nargs='?', default=None,
        help='Test phrase (default: rotates through built-in phrases)')
    parser.add_argument(
        '--iterations', type=int, default=MAX_ITERATIONS,
        help=f'Max iterations (default: {MAX_ITERATIONS})')
    parser.add_argument(
        '--no-unity', action='store_true',
        help='Skip Unity playback; analyze audio + visemes only')
    parser.add_argument(
        '--reset-params', action='store_true',
        help='Delete lipsync_params.json and start from defaults')
    args = parser.parse_args()

    if args.reset_params and os.path.exists(PARAMS_FILE):
        os.remove(PARAMS_FILE)
        print(f"[reset] Deleted {PARAMS_FILE}", flush=True)

    run(text=args.text, iterations=args.iterations, no_unity=args.no_unity)


if __name__ == '__main__':
    main()
