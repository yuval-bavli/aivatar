"""Automated alignment verification harness.

Scores how accurately each scheduled viseme lands inside its source word's
audio window, without requiring Unity or a human in the loop.

Run:
    .venv/Scripts/python -m sound_engine.tts.align_verify

Exit code 0 = all phrases pass all thresholds. Non-zero = failures (details in JSON).
"""

import asyncio
import json
import os
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

from sound_engine.tts.aligner import WordAligner
from sound_engine.tts.phonemizer.phonemizer import Phonemizer
from sound_engine.tts.viseme.viseme_scheduler import VisemeScheduler
from sound_engine.audio_analyzer import analyze_wav, is_speech_at


# ── Test phrases ──────────────────────────────────────────────────────────────

TEST_PHRASES = [
    "Hi!",
    "Can you say both?",
    "The quick brown fox jumps over the lazy dog.",
    "She sells seashells by the seashore.",
    "Mama made meatballs.",
    "Say the letter F very slowly.",  # fricatives + labials
    "Well done! You said hi so clearly.",
]

# ── Thresholds ────────────────────────────────────────────────────────────────

THRESHOLD_IN_WINDOW_PCT  = 0.90   # ≥90% of non-silence visemes land in their word window
THRESHOLD_MEDIAN_ERR_MS  = 50.0   # ≤50 ms median out-of-window miss
THRESHOLD_SIL_IN_SIL_PCT = 0.95   # ≥95% of v=0 events land in audio silence
# Pearson correlation not tested here (needs scipy); we use in-window% as primary signal


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pearson(xs, ys):
    """Pearson correlation between two equal-length lists."""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def _synthesize(text: str):
    """Run TTS synchronously and return (wav_bytes, duration_ms)."""
    from sound_engine.tts.providers.edge_tts_provider import EdgeTTSProvider

    async def _run():
        p = EdgeTTSProvider()
        return await p.synthesize_async(text)

    wav, dur, _ = asyncio.run(_run())
    return wav, dur


def _score_phrase(
    text: str,
    aligner: WordAligner,
    phonemizer: Phonemizer,
    scheduler: VisemeScheduler,
) -> dict:
    """
    Score a single phrase end-to-end.

    Steps:
    1. Synthesize with edge-tts → WAV.
    2. Align with faster-whisper → word_timings (ground truth).
    3. Build scheduled visemes using word_timings.
    4. For each non-silence viseme, check if it falls within its source word window.
    5. Compute metrics.
    """
    t0 = time.perf_counter()

    # 1. Synthesize
    try:
        wav_bytes, duration_ms = _synthesize(text)
    except Exception as e:
        return {"phrase": text, "error": f"synthesis failed: {e}", "pass": False}

    synth_ms = (time.perf_counter() - t0) * 1000

    # 2. Align (ground truth word timings)
    t1 = time.perf_counter()
    word_timings = aligner.align(wav_bytes, text)
    align_ms = (time.perf_counter() - t1) * 1000

    if word_timings is None:
        return {
            "phrase": text,
            "error": "alignment returned None",
            "pass": False,
            "synth_ms": round(synth_ms),
            "align_ms": round(align_ms),
        }

    word_list = [w for w in text.split() if w]
    if len(word_timings) != len(word_list):
        return {
            "phrase": text,
            "error": f"word count mismatch: {len(word_list)} src vs {len(word_timings)} timings",
            "pass": False,
        }

    # 3. Build scheduled viseme events using word-level timing
    word_phonemes = phonemizer.phonemize_word_list(word_list)
    viseme_events = scheduler.schedule(
        word_phonemes=word_phonemes,
        word_timings=word_timings,
        total_duration_ms=duration_ms,
        timing_mode="enhanced",
    )

    # 4. Audio analysis (for silence check)
    audio_profile = analyze_wav(wav_bytes)

    # Build a per-word window lookup: word_index → (start_ms, end_ms)
    word_windows = []
    for start_ms, dur_ms in word_timings:
        word_windows.append((start_ms, start_ms + dur_ms))

    # Map each scheduled viseme back to a source word by position in the event list.
    # Schedule emits phonemes word-by-word in order; we track which word we're in.
    # Strategy: for each event, find which word window it falls in.
    in_window_count = 0
    out_window_count = 0
    out_window_errors = []  # absolute distance to nearest window edge in ms

    silence_in_silence = 0
    silence_total = 0

    # Filter out the leading/trailing silence bookends (offset=0 and offset=duration)
    first_tick = viseme_events[0].audio_offset if viseme_events else 0
    last_tick = viseme_events[-1].audio_offset if viseme_events else 0

    for ev in viseme_events:
        ev_ms = ev.audio_offset / 10_000
        is_bookend = (ev.audio_offset == first_tick or ev.audio_offset == last_tick)

        if ev.viseme_id == 0:
            # Silence viseme — score silence-in-silence
            if not is_bookend:
                silence_total += 1
                if not is_speech_at(audio_profile, ev_ms):
                    silence_in_silence += 1
            continue

        # Non-silence: find which word window this ms falls in
        in_any_window = False
        nearest_err = float('inf')

        for start_ms, end_ms in word_windows:
            if start_ms <= ev_ms <= end_ms:
                in_any_window = True
                nearest_err = 0.0
                break
            err = min(abs(ev_ms - start_ms), abs(ev_ms - end_ms))
            nearest_err = min(nearest_err, err)

        if in_any_window:
            in_window_count += 1
        else:
            out_window_count += 1
            out_window_errors.append(nearest_err)

    total_non_sil = in_window_count + out_window_count
    in_window_pct = in_window_count / total_non_sil if total_non_sil > 0 else 1.0
    sil_in_sil_pct = silence_in_silence / silence_total if silence_total > 0 else 1.0

    out_window_errors.sort()
    median_err = out_window_errors[len(out_window_errors) // 2] if out_window_errors else 0.0

    # Pass/fail
    passes = (
        in_window_pct >= THRESHOLD_IN_WINDOW_PCT and
        median_err <= THRESHOLD_MEDIAN_ERR_MS and
        sil_in_sil_pct >= THRESHOLD_SIL_IN_SIL_PCT
    )

    return {
        "phrase": text,
        "pass": passes,
        "in_window_pct": round(in_window_pct * 100, 1),
        "median_err_ms": round(median_err, 1),
        "sil_in_sil_pct": round(sil_in_sil_pct * 100, 1),
        "total_non_sil_visemes": total_non_sil,
        "silence_visemes": silence_total,
        "duration_ms": round(duration_ms),
        "synth_ms": round(synth_ms),
        "align_ms": round(align_ms),
        "word_timings": [(round(s, 1), round(d, 1)) for s, d in word_timings],
        "words": word_list,
        "thresholds": {
            "in_window_pct": THRESHOLD_IN_WINDOW_PCT * 100,
            "median_err_ms": THRESHOLD_MEDIAN_ERR_MS,
            "sil_in_sil_pct": THRESHOLD_SIL_IN_SIL_PCT * 100,
        },
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    import datetime

    print("=== align_verify: loading models ===")
    aligner   = WordAligner(device="cpu", model_size="base.en")
    phonemizer = Phonemizer()
    scheduler  = VisemeScheduler()

    if not aligner.available:
        print("ERROR: WordAligner could not load faster-whisper — aborting.")
        sys.exit(1)

    results = []
    all_pass = True

    for phrase in TEST_PHRASES:
        print(f"\n>> {phrase!r}")
        result = _score_phrase(phrase, aligner, phonemizer, scheduler)
        results.append(result)

        if result.get("error"):
            print(f"  ERROR: {result['error']}")
            all_pass = False
        else:
            status = "PASS" if result["pass"] else "FAIL"
            print(f"  {status} | in_window={result['in_window_pct']}% "
                  f"median_err={result['median_err_ms']}ms "
                  f"sil_in_sil={result['sil_in_sil_pct']}% "
                  f"synth={result['synth_ms']}ms align={result['align_ms']}ms")
            if not result["pass"]:
                all_pass = False
                # Print per-word timings for debugging
                for w, (s, d) in zip(result["words"], result["word_timings"]):
                    print(f"    {w!r}: {s:.0f}–{s+d:.0f} ms")

    # Write JSON artifact
    os.makedirs("debug/logs", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"debug/logs/align_verify_{ts}.json"
    with open(out_path, "w") as f:
        json.dump({"results": results, "all_pass": all_pass}, f, indent=2)
    print(f"\nResults written to {out_path}")

    if all_pass:
        print("\nAll phrases passed all thresholds.")
        sys.exit(0)
    else:
        print("\nSome phrases FAILED -- see JSON for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
