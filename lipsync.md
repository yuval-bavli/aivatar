# Lip Sync — Investigation & State of Play

**Last updated: 2026-05-01 (Attempt 13 — audio-aware silence handling for inter-sentence pauses).**

> **Attempt 13 update (2026-05-01)**: User reported the mouth keeps moving during the
> sub-second pause after a period (e.g. between sentences). Two stacked causes:
>
> **Root cause 1 — Docker TTS server has no numpy/torch.** The `Dockerfile.tts` only
> installs `sound_engine/requirements.txt` (edge-tts, nltk, requests, dotenv, pydub) —
> no numpy, no torchaudio. So `PhonemeAligner` and `WordAligner` both fail to load and
> the server falls back to `schedule_sentences()`. (Confirmed in
> `debug/logs/tts_server/tts_server_*.log`: `PhonemeAligner init failed (No module
> named 'numpy') — disabled`.)
>
> **Root cause 2 — `schedule_sentences` distributes phonemes across the *boundary*
> window, not the *speech* window.** edge-tts SentenceBoundary durations include the
> trailing silence between sentences. For "The grass is green. Say it with me, the
> grass is green.": boundary 1 = 100–2088ms, boundary 2 = 2038–4988ms. Actual audible
> speech (RMS analysis): 200–1190ms then 2300–4140ms. The scheduler stretches sentence
> 1's 12 phonemes across 1988ms (≈165ms each) instead of the actual 1000ms (≈83ms
> each), so the last phonemes of "green" land at ~1925ms — well inside the audible
> silence (1190–2300ms). The Unity `continuousCrossfade` path then ramps toward the
> next sentence's phonemes across the whole 1100ms gap, so the mouth keeps animating
> during the pause.
>
> **Fix (Python)** — `sound_engine/tts/speech_synthesizer.py`:
> - New `_clip_boundaries_to_audio()`: runs `audio_analyzer.analyze_wav()` (pure
>   stdlib, no numpy needed) to detect speech regions, then tightens each edge-tts
>   sentence boundary to the speech regions whose centers fall inside it. Speech
>   regions are claimed by the first matching boundary so overlapping edge-tts
>   boundaries don't double-claim.
> - New `_inject_pause_silences()`: backstop for any scheduling path — inserts a v=0
>   event at the start of any silence region ≥ 200ms (excluding the leading/trailing
>   bookends, which the scheduler already emits). Applied after all three scheduling
>   paths (`schedule_phoneme_timings`, `schedule_sentences`, `schedule`).
> - `_build_visemes()` now takes `wav_bytes` so post-processing can run.
>
> **Fix (Unity)** — `unity/aivatar/Assets/Scripts/AnimClipLipSync.cs`:
> Added a `curId == 0` branch to the `continuousCrossfade` path. Mirror of the
> existing `nextId == 0` close-out: when the *current* viseme is silence and the
> *next* is non-silence, hold the rest pose until `nextMs - closeOutMs`, then ramp
> the next viseme up linearly over `closeOutMs`. Without this, even with explicit
> silence events the mouth would still ramp the next viseme up across the whole
> silence gap.
>
> **Verified output** (post-fix, "The grass is green. Say it with me, the grass is green."):
> ```
>  1109.5 ms  v=8     N — last phoneme of "green"
>  1190.0 ms  v=0     silence at start of inter-sentence pause (matches RMS exactly)
>  2300.0 ms  v=7     S — first phoneme of "Say" (matches phoneme aligner ground truth)
> ```
> Sentence 1 phonemes now cleanly fit 200–1190ms (was 100–2088ms with the boundary
> stretch). The 1110ms inter-sentence silence is honest in the timeline; Unity's
> open-from-silence branch keeps the mouth at rest until 2150ms, ramps to S by 2300ms.
>
> **Changed files**:
> - `sound_engine/tts/speech_synthesizer.py` — `_clip_boundaries_to_audio`,
>   `_inject_pause_silences`, and `_build_visemes(wav_bytes=...)` plumbing.
> - `unity/aivatar/Assets/Scripts/AnimClipLipSync.cs` — added `curId == 0` branch in
>   `UpdateTargets()` (mirror of `nextId == 0` close-out).
>
> **Note**: This works *without* the phoneme aligner. If numpy/torch are added to the
> Docker image later, `PhonemeAligner` becomes the primary path and these fixes
> become belt-and-suspenders (still useful: silence injection from audio is a
> correctness backstop, and the Unity open-from-silence branch is needed regardless
> of how silence events get into the timeline).

---

**Previous: 2026-04-25 (Attempt 12 — phoneme-level MMS_FA alignment + Slerp rotation fix + sync oracle).**

> **Attempt 12 update (2026-04-25)**: Three stacked issues resolved simultaneously.
>
> **Root cause 1 — Iterative Slerp under-rotates jaw on every crossfade frame (Unity):**
> `AnimClipLipSync.SmoothAndApply()` accumulated rotations via `rot = Slerp(rot, pose[v], weight[v])`
> iterated over all 14 visemes. With `continuousCrossfade=true`, two visemes are always
> simultaneously active, making this fire on **every frame**. The jaw never opened as far as the
> baked FBX viseme intends — TH's extreme jaw drop and AA's wide open became indistinguishable
> on screen. Fix: find top-2 visemes by weight, apply a clean two-viseme Slerp.
>
> **Root cause 2 — Within-word phoneme timing still approximate (Python):**
> The MMS_FA word-level aligner (Attempt 11) gave accurate word boundaries, but phonemes inside
> each word were still placed by static category weights (`_distribute()` with vowels 1.5×, stops
> 0.6×…). For a word like "seashells" (5 phonemes across 600ms), individual phonemes could drift
> ±150ms from their true audio position.
>
> **Fix**: Replaced faster-whisper word aligner with `torchaudio.pipelines.MMS_FA` phoneme aligner
> (`sound_engine/tts/phoneme_aligner.py`). MMS_FA runs forced alignment on the actual TTS audio,
> returning per-character TokenSpan objects from the real audio signal. Phonemes within each word
> are then pro-rated by character-span durations (characters that consume more audio time give their
> phonemes proportionally more time). New scheduler path: `VisemeScheduler.schedule_phoneme_timings()`.
>
> **Latency impact**: MMS_FA on GPU (warm model) = **14ms** vs ~400ms for whisper on CPU. Net
> saving of ~380ms per TTS call. Total `/speak` latency: edge-tts synthesis (~0.5–1.5s) + 14ms.
>
> **Root cause 3 — No ground-truth verification (tooling):**
> Built two-layer sync oracle:
> - `sound_engine/sync_oracle.py` — loads Unity frame log (with jaw_deg + lip_gap fields now
>   recorded), cross-correlates mouth signal against audio RMS, detects flat plateaus, scores 0–100,
>   and writes `debug/sync_report.png` with audio + mouth + phoneme overlay.
> - `sound_engine/sync_pixel_oracle.py` — loads PNG frames from `LipSyncFrameRecorder.cs`, runs
>   mediapipe face mesh to extract pixel lip distance, correlates against audio and bone motion.
>
> **New files**:
> - `sound_engine/tts/phoneme_aligner.py` — `PhonemeAligner` (MMS_FA, GPU)
> - `sound_engine/sync_oracle.py` — bone-motion vs audio oracle (numeric + PNG)
> - `sound_engine/sync_pixel_oracle.py` — pixel-level oracle using mediapipe
> - `unity/aivatar/Assets/Editor/LipSyncFrameRecorder.cs` — captures ~30fps PNGs during playback
>
> **Changed files**:
> - `unity/aivatar/Assets/Scripts/AnimClipLipSync.cs` — fixed `SmoothAndApply()` rotation blend;
>   extended `FrameRecord` with `jawDeg` and `lipGap` fields; cached jaw/lip bone references.
> - `sound_engine/tts/speech_synthesizer.py` — phoneme aligner is first-try, word aligner fallback,
>   sentence-level as last resort; new 8-element return tuple.
> - `sound_engine/tts/server.py` — lazy-init `PhonemeAligner`, env var `TTS_DISABLE_PHONEME_ALIGNER`
>   to opt out; falls back to word aligner if phoneme aligner unavailable.
> - `sound_engine/tts/viseme/viseme_scheduler.py` — new `schedule_phoneme_timings()` method.
> - `lipsync_params.json` — reset: `smoothAdvanceMs=0, global_offset_ms=0, time_scale=1.0`.
>
> **Verified output** (phoneme timing, post-fix):
> ```
> 'Can you say both?'  TH viseme (v=3) @ 1030ms — correct word position
> 'She sells seashells.' — SS visemes at 440ms, 635ms, 1208ms — all three S sounds distinct
> 'Hi!' — AY diphthong @ 546ms (was missing pre-Attempt 10, now present and timed correctly)
> ```

**Previous: 2026-04-24 (Attempt 11 — word-level forced alignment via faster-whisper).**

> **Attempt 11 update (2026-04-24)**: Replaced static-weight sentence-level phoneme
> distribution with word-level forced alignment using `faster-whisper base.en`.
>
> **Root cause of "TH fires at wrong moment"**: `edge-tts` v7+ only emits
> `SentenceBoundary` events. `schedule_sentences()` distributes phonemes across the
> full sentence window using static phoneme-category weights. This is accurate on
> average, but individual words can drift 200–600ms from their actual audio position
> when sentence prosody doesn't match the flat distribution.
>
> **Fix**: After `edge-tts` returns the WAV, run `faster-whisper base.en` with
> `word_timestamps=True` to get per-word `(start_ms, dur_ms)` windows. If alignment
> succeeds, route through the existing `schedule()` (word path) instead of
> `schedule_sentences()`. On failure, fall back transparently.
>
> **New files**:
> - `sound_engine/tts/aligner.py` — `WordAligner` class (loads `base.en` once, exposes
>   `align(wav_bytes, source_text) -> list[(start_ms, dur_ms)] | None`)
> - `sound_engine/tts/align_verify.py` — automated harness; runs 7 test phrases end-to-end
>   and scores viseme placement against whisper ground truth.
>
> **Changed files**:
> - `sound_engine/tts/speech_synthesizer.py` — after edge-tts, calls
>   `word_aligner.align()` in a thread; on success swaps `sentence_boundaries` for
>   `word_timings` so `_build_visemes()` takes the word path.
> - `sound_engine/tts/server.py` — lazy-initialises `WordAligner` at startup; attaches
>   to the shared `SpeechSynthesizer` instance.
> - `sound_engine/tts/viseme/viseme_scheduler.py` — fixed `schedule()` to skip `vid==0`
>   phonemes inside words (consistent with `schedule_sentences()`; prevents L/HH from
>   causing mid-word mouth-close).
>
> **Results** (automated harness `align_verify.py`):
> - 7/7 test phrases pass all thresholds (in-window ≥90%, median err ≤50ms, silence ≥95%)
> - Alignment latency: ~400ms per clip on CPU (base.en int8)
> - Live test: "Can you say both?" — TH viseme (v=3) fires at 1086ms, exactly within
>   the "both" word window (whisper reports "both" at ~890–1400ms after onset clamping)
> - Caveats: whisper cannot reliably align words it mis-transcribes (e.g. "Twelfth" → 
>   "12th"); those fall back to sentence-level timing (existing behavior, no regression).

**Previous: 2026-04-24 (Attempt 10 — AY diphthong mapping bug).**

> **Attempt 10 update (2026-04-24)**: Found a critical bug in
> `arpabet_to_viseme.py`: the diphthong `AY` (the vowel in "hi", "my",
> "try", "fine") was missing from `ARPABET_TO_VISEME` and silently fell
> through to `0` (silence). Every word containing `AY` produced zero
> mouth motion, and the Attempt 9 optimizer's `time_scale=0.6934` was
> partly compensating for this missing-event shrinkage.
>
> **Fix**: `'AY': 10` added to the vowel group (open/unrounded, visually
> similar to AA/AE).
>
> **Reset**: `lipsync_params.json` set to `time_scale=1.0, global_offset_ms=0`
> since the optimizer's convergence was against a phrase that happened to
> avoid `AY`. After the mapping fix the raw timeline matches actual speech
> within ~4% drift for a 4-sentence test phrase (7494ms scheduled span vs
> 7210ms actual speech window, drift=1.04). Re-running the optimizer on
> representative phrases may further refine these.

**Previous: 2026-04-14 (Automated optimizer — see Attempt 9). Visual result: significant improvement confirmed by user.**

> **Attempt 8 update**: Fixed two remaining bugs causing post-audio
> mouth motion and a lingering "stuck viseme" on the last phoneme before
> silence. Validator passed with "thank you very much" — 11 distinct
> non-zero visemes animated, topWeight=0.000 within 100ms of audio end.
>
> **Bug 1 fix (close-to-silence window anchored wrong)**: When the next
> viseme is silence (v=0), the old code computed the close window from
> `nextMs - closeOutMs` (i.e., held the last phoneme until 150ms before
> the silence event). Fixed to start the close immediately from `curMs`:
> `windowEnd = Min(curMs + closeOutMs, nextMs)`. Mouth now begins
> closing the instant the last phoneme fires.
>
> **Bug 2 fix (end detection too slow)**: Old guard was
> `playFrameCount > 30 && wallElapsed > _clipDuration + 0.2f` — up to
> 700ms of extra animation after audio ended. Replaced with two checks:
> (a) `!audioSource.isPlaying && playFrameCount > 10 && wallElapsed > _clipDuration * 0.3f`
> (stops immediately when audio reports done) and (b) `wallElapsed > _clipDuration + 0.05f`
> (50ms grace cap). `isLipSyncPlaying` now goes false within one frame of
> audio end.
>
> **Bug 3 fix (validator mid-playback screenshot)**: `LipSyncValidator`
> used `_audioSource.time > _clipLength * 0.4f` to trigger the mid-
> playback screenshot, which never fired because Unity 6 streaming clips
> return `audioSource.time = 0`. Fixed to use
> `elapsed - _audioStartWallTime > _clipLength * 0.4f` (wall clock).
> All 3 screenshots now captured on every run.
>
> ---
>
> **Attempt 7 update**: After Attempt 6 the validator passed but visually
> the mouth still looked robotic — holding AH static for ~750ms then
> snapping to OW. Root cause: `UpdateTargets` held `curId` at weight=1.0
> until within `lookAheadMs` (80ms) of the next event. On sparse
> timelines that means 600ms+ of zero motion between events.
>
> **Fix**: `continuousCrossfade` mode in `AnimClipLipSync` —
> eases current→next viseme across the **whole gap** so the mouth is
> always in motion. `crossfadeEase` (default 1.5) biases the curve
> toward the current viseme so transitions still read as articulated.
> Also dropped `smoothAdvanceMs` default 100 → 40 to reduce lead.
>
> ---
>
> **Earlier TL;DR (Attempts 1–6)**: Resolved three stacked bugs:
> on top of each other:
> (1) `AH` mapped to v=13 → "Hello" collapsed to one viseme after dedup
>     (Attempt 5 — arpabet_to_viseme.py);
> (2) `Application.runInBackground=false` → Unity's game loop froze at
>     frame 1 whenever the editor lost focus, so `Time.time`, audio, and
>     `Update()` never advanced during MCP-driven tests (Attempt 6);
> (3) Unity 6 `AudioSource.time`/`timeSamples` returns 0 for clips
>     created via `AudioClip.Create` + `SetData` / callbacks — needs a
>     `Time.realtimeSinceStartup` fallback (Attempt 6).
>
> All three fixed in `AnimClipLipSync.cs` + `arpabet_to_viseme.py`.
> Automated validator (`LipSyncValidator.cs`) confirms: "Hello" animates
> v=10 (AH open) → v=13 (OW rounded), mouth closed after audio end.

---

## Attempt 11 — Word-level forced alignment (2026-04-24, **LANDED**)

**Problem**: Although the overall viseme timeline length matched the audio duration
(fixed in Attempt 10), individual phonemes within sentences were placed at the wrong
moments. Example: "Can you say both?" — the TH viseme fired ~300ms before the
"oth" sound was audible.

**Root cause**: `schedule_sentences()` distributes each sentence's phonemes using
static phoneme-category weights (vowels 1.5×, stops 0.6×, fricatives 1.1×…).
These weights are averages and do not capture actual word-level prosody. The
`VisemeScheduler.schedule()` method already accepted per-word timings — it was
simply never populated for the edge-tts path.

### What was built

**`sound_engine/tts/aligner.py`** — `WordAligner`:
- Loads `faster-whisper base.en` (CPU, `int8`) once at startup (~0.8s warm-up)
- `align(wav_bytes, source_text)` → `list[(start_ms, dur_ms)]` per source word
- WAV parsed to float32, resampled to 16kHz if needed
- Whisper called with `word_timestamps=True`, `beam_size=1`
- Speech onset from `audio_analyzer.analyze_wav()` used to clamp whisper's
  first-word start (whisper often reports onset 50–250ms early)
- Word matching: greedy proportional assignment handles different token counts
- Edit-distance guard: if normalized source word vs whisper token distance
  exceeds `max(2, len//2)`, returns `None` (fall back to sentence timing)
- Returns `None` on any exception — never breaks existing flow

**`sound_engine/tts/speech_synthesizer.py`** — after edge-tts returns:
```python
if self.word_aligner and self.word_aligner.available:
    word_timings = await asyncio.to_thread(self.word_aligner.align, wav_bytes, text)
    if word_timings is not None:
        return ("edge-tts+align", wav_bytes, duration_ms, None, word_timings, word_list)
# fallback:
return ("edge-tts", wav_bytes, duration_ms, sentence_boundaries, None, None)
```

**`sound_engine/tts/server.py`** — lazy-init `WordAligner` at startup:
```python
@classmethod
def get_aligner(cls):
    if cls._aligner is None:
        cls._aligner = WordAligner(device="cpu", model_size="base.en")
    return cls._aligner
```

**`sound_engine/tts/viseme/viseme_scheduler.py`** — bug fix in `schedule()`:
Added `if vid == 0: continue` inside the word loop, consistent with
`schedule_sentences()`. Previously, L and HH phonemes (which map to v=0) emitted
silence events inside words, causing mid-word mouth closing (e.g. "lazy" would
close the mouth on the L then reopen for EY).

**`sound_engine/tts/align_verify.py`** — automated harness:
Synthesizes 7 test phrases with edge-tts, aligns with whisper, schedules visemes,
then scores each non-silence viseme against its source word's audio window.

Thresholds:
- In-window ≥ 90% (viseme fires within source word's whisper-reported window)
- Median out-of-window error ≤ 50ms
- Silence-in-silence ≥ 95% (v=0 events fire during audio silence)

Run: `.venv/Scripts/python -m sound_engine.tts.align_verify`

### Results

All 7 test phrases pass all thresholds:
```
Hi!                                      PASS | in_window=100% median=0ms sil=100%
Can you say both?                        PASS | in_window=100% median=0ms sil=100%
The quick brown fox jumps over the lazy dog. PASS | in_window=100% median=0ms sil=100%
She sells seashells by the seashore.     PASS | in_window=100% median=0ms sil=100%
Mama made meatballs.                     PASS | in_window=100% median=0ms sil=100%
Say the letter F very slowly.            PASS | in_window=100% median=0ms sil=100%
Well done! You said hi so clearly.       PASS | in_window=100% median=0ms sil=100%
```

Live: `POST /speak "Can you say both?"` — TH fires at 1086ms within the
"both" window (890–1400ms). Alignment inference ~400ms CPU; total /speak
latency ~2s (was ~0.6s).

### Limitations / known fallbacks

- Words whisper mis-transcribes (e.g. "Twelfth" → "12th") exceed edit-distance
  threshold → graceful fallback to `schedule_sentences()` for that phrase.
- ElevenLabs and MockTTS paths unchanged — they already have word timings.
- Total latency increased ~0.4s. Acceptable since TTS is the bottleneck anyway.

---

## Attempt 9 — Automated optimizer (2026-04-14)

Added a signal-analysis optimization loop that measures and corrects scheduler
timing without human judgment. Key findings and what was built:

### What was discovered

**Problem 1 — Viseme timeline is stretched ~49% relative to actual speech.**
edge-tts `SentenceBoundary` durations include padding/inter-sentence silence.
The scheduler distributes phonemes across the full reported boundary duration,
so for a sentence the TTS reports as "2.5 s" the actual voiced speech may only
occupy 1.7 s. This causes every phoneme to be spread too thin.

- Measured (phrase "Hello, how are you doing today?"):
  - Audio speech window: 260–1830 ms (1570 ms span)
  - Scheduled viseme span (before fix): 218–2551 ms (2333 ms span)
  - drift_factor = 2333 / 1570 = **1.486**

**Problem 2 — Cross-correlation is the wrong tool for offset detection.**
An earlier version of the optimizer tried to detect timing offset by
cross-correlating viseme mouth-openness vs audio RMS. This failed because
sibilants ("s", "sh") have high audio energy but low mouth openness — the
two signals don't correlate well by design. The optimizer diverged,
accumulating nonsense parameter values (time_scale → 0.007, offset → −2640 ms).

Fixed by replacing cross-correlation with a direct **speech-onset comparison**:
`global_offset_ms = first_non_sil_viseme.time_ms − audio_speech_onset_ms`
This is stable, phrase-independent, and deterministic.

### Fixes applied automatically (written to `lipsync_params.json`)

After 5 iterations on a single phrase, the optimizer converged:

| Metric | Before | After |
|--------|--------|-------|
| drift_factor | 1.486 | 1.030 |
| onset offset | −42 ms | −42 ms (within 50 ms threshold, no fix needed) |
| `time_scale` | 1.000 | 0.693 |
| `global_offset_ms` | 0.0 ms | +67.0 ms |
| scheduling score | 26.2 | 39.2 |

Score progression: **26.2 → 27.6 → 33.4 → 37.9 → 39.2 → 39.2** (stable).

**Visual result (2026-04-14): user confirmed significant improvement** after applying the optimized `lipsync_params.json` (`time_scale=0.693`, `global_offset_ms=67.0`). This is the first iteration where the timing correction produced a noticeable perceptual improvement.

**Score ceiling without Unity**: ~40/100. This is expected — audio RMS and
viseme mouth-openness are imperfectly correlated even with perfect timing
(plosives have low RMS during closure; sibilants have high RMS with moderate
mouth opening). The full 0–100 score requires Unity animation data.

The residual −42 ms onset offset (visemes open 42 ms *before* audio onset) is
intentional coarticulation anticipation, within normal range.

### New files (Attempt 9)

| File | Purpose |
|------|---------|
| [sound_engine/audio_analyzer.py](sound_engine/audio_analyzer.py) | WAV → 10 ms RMS windows, speech/silence regions, energy peaks |
| [sound_engine/sync_evaluator.py](sound_engine/sync_evaluator.py) | Onset-based offset detection, drift measurement, 0–100 scoring |
| [sound_engine/param_config.py](sound_engine/param_config.py) | `lipsync_params.json` store; `apply_fixes()` with 50% damping + bounds |
| [sound_engine/lipsync_iterator.py](sound_engine/lipsync_iterator.py) | Orchestration loop; triggers Unity via agent bridge |
| [unity/aivatar/Assets/Editor/LipSyncIterator.cs](unity/aivatar/Assets/Editor/LipSyncIterator.cs) | Unity side: reads test input, enters play mode, records animation frames, writes log |

Modified: `viseme_scheduler.py` (accepts `global_offset_ms`, `time_scale`),
`speech_synthesizer.py` (carries params), `server.py` (hot-reloads `lipsync_params.json`),
`AnimClipLipSync.cs` (adds `recordFrames` mode + `GetFrameLogJson()`).

### How to run

```bash
# Restart server first (required when server.py was changed)
# Kill old server, then:
.venv/Scripts/python sound_engine/server.py &

# Run optimizer (audio analysis only, no Unity needed for scheduler tuning)
.venv/Scripts/python -m sound_engine.lipsync_iterator --no-unity --iterations 6

# Reset params and start over
.venv/Scripts/python -m sound_engine.lipsync_iterator --no-unity --reset-params

# Full loop including Unity animation measurement (Unity Editor must be open)
.venv/Scripts/python -m sound_engine.lipsync_iterator --iterations 5
```

### Key lessons

1. **Don't rotate phrases between iterations.** Each phrase has different audio, so
   fixes for phrase 1 corrupt phrase 2. Fix one phrase until stable, then validate
   on others.

2. **Apply fixes with damping (50%).** Full correction per iteration causes
   oscillation. Damped corrections converge in 4–5 iterations.

3. **Bound all parameters.** Without bounds, unclamped accumulation collapses
   `time_scale` → 0 and `global_offset_ms` → −∞.

4. **Audio-vs-openness Pearson correlation tops out at ~0.56 with good timing.**
   This is a physics ceiling, not a bug. The full sync score (0–100) must
   incorporate Unity animation data (actual bone/blendshape motion vs audio).

5. **The 49% drift is real and consistent.** edge-tts sentence boundaries report
   wall-clock duration including silence padding. The scheduler needs `time_scale ≈
   0.69` to map scheduled phoneme spans onto actual voiced speech spans.

---

## Pipeline overview

```
edge-tts → MP3 → WAV (pydub/ffmpeg) → VisemeScheduler → VisemeEvent list
        → HTTP JSON → AzureSpeechManager → VisemeTimeline
        → AnimClipLipSync.Update() → SmoothDamp → bone poses
```

### Key files

| File | Role |
|------|------|
| [sound_engine/tts/edge_tts_provider.py](sound_engine/tts/edge_tts_provider.py) | Calls `edge_tts.Communicate`, captures `SentenceBoundary` events, returns `(wav_bytes, duration_ms, sentence_boundaries)` |
| [sound_engine/speech_synthesizer.py](sound_engine/speech_synthesizer.py) | Orchestrates TTS → phonemizer → scheduler. Calls `schedule_sentences()` for edge-tts path |
| [sound_engine/phonemizer/phonemizer.py](sound_engine/phonemizer/phonemizer.py) | CMU dict lookup + rule fallback for ARPABET |
| [sound_engine/viseme/arpabet_to_viseme.py](sound_engine/viseme/arpabet_to_viseme.py) | ARPABET → viseme ID table (0..14) |
| [sound_engine/viseme/viseme_scheduler.py](sound_engine/viseme/viseme_scheduler.py) | `schedule_sentences()` — distributes words by phoneme count, phonemes by enhanced weights |
| [sound_engine/server.py](sound_engine/server.py) | HTTP endpoint at POST /speak, `timing_mode='enhanced'` |
| [sound_engine/wav/wav_encoder.py](sound_engine/wav/wav_encoder.py) | `mp3_to_wav` via pydub — **does NOT strip MP3 priming silence** |
| [unity/aivatar/Assets/Scripts/AzureSpeechManager.cs](unity/aivatar/Assets/Scripts/AzureSpeechManager.cs) | **Rewritten (Attempt 9)** — calls local `sound_engine` server via `UnityWebRequest`. No longer uses Azure SDK. Decodes WAV + viseme events, builds `VisemeTimeline`, calls `LipSyncBase.Play()` |
| [unity/aivatar/Assets/Scripts/AnimClipLipSync.cs](unity/aivatar/Assets/Scripts/AnimClipLipSync.cs) | Lip-sync driver — bakes viseme poses from `viseme_animation.fbx`, drives bones on `targetRoot` (separate visible model) via `SmoothDamp`. Realtime fallback when `AudioSource.time` stuck at 0 (Unity 6). `recordFrames` mode for optimizer. |
| [unity/aivatar/Assets/Editor/LipSyncValidator.cs](unity/aivatar/Assets/Editor/LipSyncValidator.cs) | Self-validation — polls `AnimClipLipSync` during play mode, 3 screenshots, writes `lipsync_validation.txt` |
| [unity/aivatar/Assets/Editor/LipSyncIterator.cs](unity/aivatar/Assets/Editor/LipSyncIterator.cs) | Optimizer bridge (Attempt 9) — reads `lipsync_test_input.json`, enters play mode, injects audio+visemes directly, records frames, writes `lipsync_anim_log.json` |
| unity/aivatar/Assets/Models/Avatar/viseme_animation.fbx | 15 viseme poses at frames 0,10,...,140 at 30fps |

### Azure viseme IDs (0..14)
`0 sil`, `1 PP`, `2 FF`, `3 TH`, `4 DD`, `5 kk`, `6 CH`, `7 SS`, `8 nn`, `9 RR`, `10 aa (AA,AE,AH)`, `11 E`, `12 ih`, `13 oh (AO,OW,AW)`, `14 ou`

---

## History of fix attempts

### Attempt 1 — SentenceBoundary distribution (landed)
edge-tts v7 only emits `SentenceBoundary` events (v6 emitted `WordBoundary`
but v6 now gets 403 from the MS endpoint). Previously the code fell back
to equal-split across the entire audio, which put visemes at t=0 (wrong —
actual speech starts ~100 ms in).

**Fix**: `EdgeTTSProvider` captures `SentenceBoundary` (text, offset, duration
in 100 ns ticks), and distributes words equally within each sentence window.

### Attempt 2 — SmoothDamp compensation + phoneme-weighted distribution (landed)

**Unity side** ([AnimClipLipSync.cs](unity/aivatar/Assets/Scripts/AnimClipLipSync.cs)):
- `smoothTime` default: `0.08` → `0.05` → **`0.03`** (current)
- New field `smoothAdvanceMs` (default currently **`100f`**, range 0..300) — shifts timeline forward to compensate for SmoothDamp rise time, MP3 priming silence, and Windows DSP buffer
- New field `audioLatencyMs` (default `0f`, range -100..100) — platform tuning knob
- `lookAheadMs`: `150f` → **`80f`** (current)
- Timeline-end decay: when `lastVisemeIndex >= Count-1` (trailing silence event), `targetWeights` is cleared immediately so SmoothDamp decays to rest without waiting for `AudioSource.time == 0`

**Python side**:
- `EdgeTTSProvider.synthesize_async()` now returns **raw sentence boundaries** `[(sent_text, start_ms, dur_ms), ...]` instead of pre-distributed word events
- `SpeechSynthesizer._build_visemes()` calls new `VisemeScheduler.schedule_sentences()`
- `schedule_sentences()` distributes each sentence's duration across words **weighted by phoneme count**, then distributes phonemes within each word via `_distribute()` (`enhanced` mode — vowels 1.5×, stops 0.6× etc.)
- Silence event inserted at each sentence end (so the mouth returns to rest between sentences)

### Attempt 3 — L → v0, smoothTime → 0.03, skip v0 inside words (landed, DID NOT FIX THE SYMPTOM)

**Problem observed**: Even after Attempts 1 & 2, the user reported that
"Hello" makes the mouth open *twice* (once for "Hel", once for "lo") and
the mouth is still in an open "oh" shape when audio ends.

**Python investigation** — verified the actual server output for "Hello":
```
   0.0 ms  v=0    HH (silence — H is mapped to v0)
 397.5 ms  v=13   AH (first open)
 843.8 ms  v=0    L  (mouth CLOSES mid-word — HERE'S THE BUG)
1141.2 ms  v=13   OW (second open)
1587.5 ms  v=0    end-of-sentence silence
total duration: 1608.0 ms
```
So the "double open" was **real** and originated in the scheduler emitting
a v0 event mid-word for `L` (which was earlier mapped to v0 to avoid the
nasal-dip from L→v8). Even though L→v0 eliminated the "tongue-up dip",
it introduced a "closure dip" instead.

**Fixes applied**:
1. [sound_engine/viseme/arpabet_to_viseme.py](sound_engine/viseme/arpabet_to_viseme.py) — kept `L → 0` (viseme 0 silence)
2. [sound_engine/viseme/viseme_scheduler.py](sound_engine/viseme/viseme_scheduler.py) — in `schedule_sentences()` inner phoneme loop, **skip phonemes whose `vid == 0`**. This means silent phonemes (HH, L) inside a word don't break vowel continuity. Sentence-end silence events (emitted outside the loop) are unaffected.
3. [unity/aivatar/Assets/Scripts/AnimClipLipSync.cs](unity/aivatar/Assets/Scripts/AnimClipLipSync.cs) — `smoothAdvanceMs` default `54f` → `100f`

**Server output after Attempt 3 — verified correct**:
```
=== 'Hello' ===
duration: 1608.0 ms
    0.0 ms  v=0      leading silence
  397.5 ms  v=13     single open mouth for whole word
 1587.5 ms  v=0      end-of-sentence close
```
Exactly 3 events as intended.

**Result**: **User reports no visible change**. Mouth still opens twice on
"Hello", still trails past audio end.

### Attempt 4 — Kill stale server + fix scene-serialized values (2026-04-12, partial fix)

**Root cause 1 — stale HTTP server process**:
Three zombie Python processes were still LISTENING on port 5123, all
launched before any of Attempts 1–3. The running server had the pre-fix
`L→v8` mapping and no `vid == 0` skip, so it was still returning 5 events
for "Hello" (`0→13→8→13→0` — the exact double-open pattern).

Verified by comparing:
```
# Direct Python call (disk code — correct):
  3 events:  0.0 v=0  |  397.5 v=13  |  1587.5 v=0

# Running HTTP server at 127.0.0.1:5123 (stale):
  5 events:  0.0 v=0  |  402.0 v=13  |  804.0 v=8  |  1206.0 v=13  |  1608.0 v=0
```

Fix: `taskkill /F` on all three PIDs (74392, 84856, 49272), then
`.venv/Scripts/python sound_engine/server.py`. After restart, server
returns 3 events as expected.

**Root cause 2 — stale scene-serialized AnimClipLipSync values**:
Unity preserves serialized field values on existing components even when
the `.cs` default changes (by design — domain reload doesn't overwrite
Inspector values). The `Avatar` GameObject in `scene1.unity` still had
Attempt 2's tuning:

| Field            | Scene (stale) | Code default |
|------------------|---------------|--------------|
| `smoothTime`     | `0.08`        | `0.03`       |
| `lookAheadMs`    | `150`         | `80`         |
| `smoothAdvanceMs`| `90`          | `100`        |

Fix: set properties via MCP `manage_components` to match code defaults,
saved scene.

**Validation**:
- Unity console: `[AnimClipLipSync] Play() — visemes=3 clip=1.61s` ✓
- Post-audio game-view screenshot shows mouth in neutral/closed position ✓
- No code changes were needed — disk code was already correct from Attempt 3

**However**: user still reported only one visible mouth shape for "Hello".
The stale-server fix was necessary but not sufficient — see Attempt 5.

### Attempt 5 — Move AH from viseme 13 to viseme 10 (2026-04-12, **FIXED**)

**Problem observed**: Even with 3 correct events (`v=0 → v=13 → v=0`),
"Hello" only showed one mouth shape. The word has two vowels (AH and OW)
that should look different, but both were mapped to v=13 ("oh"/rounded).
After the scheduler skips `HH→v0` and `L→v0`, `AH→v13` and `OW→v13`
are consecutive identical IDs → deduplicated to one event.

**Root cause**: `AH` (ʌ, as in "hut"/"hello") is an open unrounded vowel,
visually similar to `AA`/`AE` (already at v=10), not to `AO`/`OW` (rounded
back vowels at v=13). The Azure 22-viseme system confirms: AH groups with
AE (viseme 1: `æ, ə, ʌ`), not with AO/OW.

**Fix applied**:
- [sound_engine/viseme/arpabet_to_viseme.py](sound_engine/viseme/arpabet_to_viseme.py) —
  moved `'AH': 13` → `'AH': 10`

**Server output after Attempt 5 — verified correct**:
```
=== 'Hello' ===
duration: 1608.0 ms
    0.0 ms  v=0      leading silence
  397.5 ms  v=10     AH — open mouth ("aa" shape)
 1141.2 ms  v=13     OW — rounded mouth ("oh" shape)
 1587.5 ms  v=0      end-of-sentence close
```
4 events, two visually distinct mouth shapes.

**Result**: Server confirmed. Unity testing pending.

### Attempt 8 — Fix post-audio lag and stale close-out window (2026-04-13, **VALIDATED**)

**Problem observed**: After Attempt 7, the animation was less robotic but
the mouth continued moving after audio ended ("BOOP BOOP BOOP" and "thank
you" still had trailing viseme motion). Also the last phoneme before silence
was held statically because the close-out window was anchored at the wrong end.

**Bug 1 — close-to-silence window anchored at wrong end** ([AnimClipLipSync.cs](unity/aivatar/Assets/Scripts/AnimClipLipSync.cs)):
Old: `windowStart = nextMs - closeOutMs` — mouth holds last phoneme until
150ms before silence event. For a 500ms gap, that's 350ms of hold while
audio is already trailing silent.
Fix: start closing immediately from `curMs`:
```csharp
float windowEnd = Mathf.Min(curMs + closeOutMs, nextMs);
float t = Mathf.Clamp01((elapsedMs - curMs) / Mathf.Max(1f, windowEnd - curMs));
targetWeights[curId] = 1f - t;
```

**Bug 2 — end detection too slow** ([AnimClipLipSync.cs](unity/aivatar/Assets/Scripts/AnimClipLipSync.cs)):
Old: `playFrameCount > 30 && wallElapsed > _clipDuration + 0.2f` → up to
700ms extra animation after audio end (`playFrameCount > 30` alone = 500ms
at 60fps). Fixed to:
```csharp
bool audioStopped = !audioSource.isPlaying && playFrameCount > 10
                    && wallElapsed > _clipDuration * 0.3f;
bool pastClipEnd = playFrameCount > 10 && wallElapsed > _clipDuration + 0.05f;
```
`isLipSyncPlaying` now goes false within one frame of audio reporting done.

**Bug 3 — validator mid-playback screenshot never fires** ([LipSyncValidator.cs](unity/aivatar/Assets/Editor/LipSyncValidator.cs)):
`_audioSource.time > _clipLength * 0.4f` always stayed false because Unity
6 streaming clips return `audioSource.time = 0`. Fixed to wall-clock elapsed:
```csharp
float audioWallElapsed = elapsed - _audioStartWallTime;
if (_audioStarted && !_audioEnded && _screenshotPhase == 0 &&
    audioWallElapsed > _clipLength * 0.4f)
```

**Validator result** — "thank you very much":
```
Distinct non-zero visemes seen: 11 (3,10,8,5,12,14,2,11,9,1,6)
Multiple visemes animated: PASS
Mouth closed after audio: PASS
topWeight at +500ms post-audio: 0.000
```
isLipSyncPlaying went false at [2.46s], 50ms after AUDIO ENDED [2.41s].
All 3 screenshots captured (mid_playback, at_audio_end, after_audio_end_500ms).

---

### Attempt 7 — Continuous crossfade across whole gap (2026-04-13, **FIXED robotic look**)

**Problem observed**: Even with correct timelines and passing validator,
the mouth visually looked robotic — for "Hello" it opened to AH, froze
for ~750ms, jumped to OW, froze ~450ms, then closed.

**Root cause**: `AnimClipLipSync.UpdateTargets` only crossfaded in the
last `lookAheadMs` (80ms) before the next event. Between events it set
`targetWeights[curId] = 1f` statically. edge-tts speaks slowly (1.6s for
"Hello"), the scheduler skips `v=0` consonants (Attempt 3), and Azure
viseme consolidation produces only a handful of events per word — so
each viseme was commanded to hold for 500–750ms of pure stasis.

**Fix** in [AnimClipLipSync.cs](unity/aivatar/Assets/Scripts/AnimClipLipSync.cs):
- New field `continuousCrossfade` (default `true`) — in `UpdateTargets`,
  when `nextId != curId`, blend `t = clamp01((elapsedMs - curMs) / gap)`
  then `blend = pow(t, crossfadeEase)` and set
  `targetWeights[curId] = 1 - blend`, `targetWeights[nextId] = blend`.
  Mouth is always in motion.
- New field `crossfadeEase` (default `1.5`, range 0.5–4) — exponent on
  progress `t`. 1.0 = linear morph (looks slurred), >1 holds current
  viseme longer before a faster transition (reads as articulation).
  Sweet spot 1.5–2.0 for edge-tts's slow default rate.
- `smoothAdvanceMs` default dropped 100 → 40 (the 100ms lead was
  overshooting when the realtime fallback kicked in since that fallback
  has no inherent audio latency).

**Scene values updated** on `Avatar.AnimClipLipSync` via MCP to match:
`smoothAdvanceMs=40`, `continuousCrossfade=true`, `crossfadeEase=1.5`.

**Follow-up fix (same day)** — mouth continued moving after audio ended.
Cause: `continuousCrossfade` was blending the last vowel → trailing
silence (`v=0`) across the whole gap. For "Hello", `OW@1141ms` →
`v=0@1608ms` = a 467ms slow-close — most of it during the WAV's
trailing silence padding, so the mouth kept closing while audio was
already silent.

Fix: when `nextId == 0`, clamp the crossfade window to `closeOutMs`
(default 150ms) and use linear (not eased) blend. Mouth holds the
vowel until 150ms before the silence event, then snaps shut. Applied
to the scene via MCP.

**Tuning notes for future**:
- Too morphy/slurred → raise `crossfadeEase` to 2–3
- Visemes fire too early → raise `smoothAdvanceMs`
- Visemes fire too late → lower `smoothAdvanceMs` toward 0 or negative

**Lesson learned (new)**:
7. **A passing validator is not a passing animation.** The validator
   checked "≥2 distinct visemes seen" and "mouth closed after audio",
   both of which passed in Attempt 6 while the animation still looked
   robotic. "Distinct visemes seen" doesn't catch "each viseme held
   statically for 700ms". Future validators should sample the weight
   curve and fail on long flat plateaus.

### Attempt 6 — runInBackground + realtime fallback + self-validator (2026-04-13, **FIXED end-to-end**)

After Attempt 5 the server returned correct events but Unity *still* looked
out of sync when driven from MCP. The user asked for a self-validation
loop so iteration didn't depend on manual visual inspection.

**Built**: [unity/aivatar/Assets/Editor/LipSyncValidator.cs](unity/aivatar/Assets/Editor/LipSyncValidator.cs).
Hooks `EditorApplication.update`, polls `AnimClipLipSync.GetDiagnostics()`
every ~100 ms during a play-mode session, captures three Game-view
screenshots (mid-playback, at audio-end, +500 ms after audio-end) and
writes a pass/fail report to `lipsync_validation.txt`. Verdict checks:
(a) ≥2 distinct non-zero `topViseme` values seen, (b) `topWeight < 0.05`
500 ms after audio ends.

Invoked via the file-based agent bridge:
```bash
printf 'execute LipSyncValidator.Run' > agent_request.txt
```

**Bug A — game loop frozen at frame 1 when editor unfocused**:
Validator output showed `frame=1` constant across 10 s while
`Time.realtimeSinceStartup` advanced normally — i.e. `Update()` was not
ticking. Cause: `Application.runInBackground` defaults to `false`, so when
MCP/Claude steals focus from the Unity Editor the player loop stalls.
Audio plays via the OS mixer either way, but `Update()` never runs so
visemes never advance.

Fix in `AnimClipLipSync.Awake()`:
```csharp
Application.runInBackground = true;
```

**Bug B — `AudioSource.time`/`timeSamples` stuck at 0 in Unity 6**:
Even with `Update()` ticking, diagnostics showed `audioMs=0
timeSamples=0 playing=True` for the entire clip. Unity 6 doesn't update
`time`/`timeSamples` reliably for clips created with `AudioClip.Create` +
streaming PCM callback — the OS mixer plays them but the AudioSource
fields stay zeroed.

Fix in `AnimClipLipSync`: stamp `_playStartRealtime =
Time.realtimeSinceStartup` and `_clipDuration = clip.length` in `Play()`,
then in `Update()` use `Time.realtimeSinceStartup - _playStartRealtime` as
the timeline cursor whenever `audioSource.timeSamples == 0 &&
audioSource.time == 0`. End detection uses wall-clock: stops immediately when `!audioSource.isPlaying`
(with startup guard), and caps at `_clipDuration + 0.05 s` (Attempt 8 tightened
from `+0.2 s` and `playFrameCount > 30` to `+0.05 s` and `playFrameCount > 10`).

**Final validator output** (`lipsync_validation.txt`):
```
Distinct non-zero visemes seen: 2 (10,13)
Multiple visemes animated: PASS
Mouth closed after audio: PASS
```
Screenshots confirm visually distinct mouth shapes mid-playback and a
closed mouth 500 ms after audio end.

---

## Current state of code (as of 2026-04-14, Attempt 9)

### [AzureSpeechManager.cs](unity/aivatar/Assets/Scripts/AzureSpeechManager.cs) — **fully rewritten**

The Azure TTS SDK (`Microsoft.CognitiveServices.Speech`) has been **removed**. The
component now calls the local `sound_engine` Python server via `UnityWebRequest`:

```csharp
[Header("Sound Engine Server")]
public string serverUrl = "http://127.0.0.1:5123";

public void Speak(string text)  // fires a coroutine
```

The coroutine POSTs `{"text": "…"}`, receives `audio_base64` + `viseme_events`,
decodes the WAV, builds an `AudioClip` with `SetData`, builds a `VisemeTimeline`
from the event array, and calls `lipSyncController.Play(timeline, clip)`.

**Why**: The Azure SDK added a large dependency and required a live subscription key.
The `sound_engine` server provides the same audio + viseme data on localhost with no
key required, using edge-tts (free) or ElevenLabs optionally.

**Before starting play mode**, the server must be running:
```bash
.venv/Scripts/python sound_engine/server.py
```

### [AnimClipLipSync.cs](unity/aivatar/Assets/Scripts/AnimClipLipSync.cs) — tuning defaults (now matching scene)

**New field `targetRoot`** — separates the animation source from the visible model:
```csharp
public GameObject animRoot;    // viseme_animation.fbx hierarchy (source of poses)
public GameObject targetRoot;  // the actual character to drive (if null: uses animRoot)
```
At `Start()`, poses are baked from `animRoot` by sampling `visemeClip` at each of
the 15 viseme frames. At runtime, those poses are applied to `targetRoot`'s bones
by matching bone names. This lets the FBX animation rig live hidden in the scene
while the visible MetaHuman/character rig gets driven separately.
`SetupAnimClipLipSync` now auto-detects `targetRoot` by finding the root-level
GameObject whose SkinnedMeshRenderer has the most facial bones (`FACIAL_*` or
`head`).

```csharp
[Range(0.01f, 0.2f)] public float smoothTime = 0.03f;
[Range(20f, 200f)]   public float lookAheadMs = 80f;
[Range(0f, 300f)]    public float smoothAdvanceMs = 40f;   // was 100 (Attempt 7)
[Range(-100f, 100f)] public float audioLatencyMs = 0f;
public bool continuousCrossfade = true;                    // Attempt 7
[Range(0.5f, 4f)] public float crossfadeEase = 1.5f;       // Attempt 7
public bool recordFrames = false;                          // Attempt 9 optimizer
```
When `continuousCrossfade=true`, `lookAheadMs` is unused — the blend
runs across the whole inter-event gap instead.
Timeline-end decay is active: `UpdateTargets` returns early with
`targetWeights` cleared when `lastVisemeIndex >= activeTimeline.visemes.Count - 1`.

**`recordFrames` mode** (Attempt 9): when `true`, each `Update()` frame appends a
`FrameRecord {timeMs, topVisemeId, topWeight, audioMs}` to an internal list.
After playback, call `GetFrameLogJson()` to retrieve a JSON array — used by
`LipSyncIterator.cs` for offline sync scoring.

Attempt 6 additions:
```csharp
void Awake() {
    audioSource = GetComponent<AudioSource>();
    Application.runInBackground = true;   // keep Update() ticking when editor unfocused
}

public override void Play(VisemeTimeline timeline, AudioClip clip) {
    ...
    _playStartRealtime = Time.realtimeSinceStartup;
    _clipDuration = clip.length;
}

// In Update(): realtime fallback when audio time APIs are stuck at 0
float audioTimeMs = (audioSource.timeSamples > 0 || audioSource.time > 0f)
    ? audioSource.time * 1000f
    : (Time.realtimeSinceStartup - _playStartRealtime) * 1000f;

// End detection: stop immediately on audioSource.isPlaying=false, or 50ms after clip length
float wallElapsed = Time.realtimeSinceStartup - _playStartRealtime;
bool audioStopped = !audioSource.isPlaying && playFrameCount > 10
                    && wallElapsed > _clipDuration * 0.3f;
bool pastClipEnd = playFrameCount > 10 && wallElapsed > _clipDuration + 0.05f;
if (audioStopped || pastClipEnd) { isPlaying = false; ... }   // Attempt 8 (was +0.2f, fc>30)

// Close-to-silence crossfade: start closing from curMs, not from nextMs-closeOutMs (Attempt 8)
if (nextId == 0) {
    float windowEnd = Mathf.Min(curMs + closeOutMs, nextMs);
    float t = Mathf.Clamp01((elapsedMs - curMs) / Mathf.Max(1f, windowEnd - curMs));
    targetWeights[curId] = 1f - t;
}
```

### [ProLipSync.cs](unity/aivatar/Assets/Scripts/ProLipSync.cs) — additions

```csharp
[Header("Sync")]
[Range(-200f, 200f)] public float audioLatencyMs = 0f;  // hardware latency compensation
[Header("Debug")]
public bool debugLog = false;  // logs each viseme transition + initial event list
```
`Play()` now logs the first 20 viseme events and clip duration when `debugLog=true`,
useful for verifying the server timeline without needing the Python command line.

### `lipsync_params.json` — optimizer parameter store (Attempt 9)

Written to repo root by the optimizer; hot-loaded by the server on every `/speak`
request (no restart needed).

```json
{
  "global_offset_ms": 67.0,
  "time_scale": 0.6934,
  "vowel_weight": 1.5,
  "consonant_weight": 0.6,
  "smoothAdvanceMs": 40.0,
  "smoothTime": 0.03,
  "crossfadeEase": 1.5
}
```

`global_offset_ms` shifts all viseme timestamps by a fixed amount after scheduling.
`time_scale` scales all durations (compresses/stretches the whole phoneme timeline).
Delete the file to reset to defaults; or run with `--reset-params`.

### [arpabet_to_viseme.py](sound_engine/viseme/arpabet_to_viseme.py)
```python
'N': 8,  'NG': 8,   # nasals only
'L': 0,             # L is a tongue gesture, mapped to neutral
'AA': 10,  'AE': 10,  'AH': 10,   # open/unrounded vowels
'AO': 13,  'OW': 13,  'AW': 13,   # rounded back vowels (AH no longer here)
```
`PHONEME_WEIGHT` still has `LIQUIDS = {'L', 'R'}` with weight 1.0 — so L still consumes its share of time in the word (then gets skipped by the scheduler).

### [viseme_scheduler.py](sound_engine/viseme/viseme_scheduler.py) `schedule_sentences()`
```python
for phone, offset_ms in zip(phones, offsets):
    vid = phoneme_to_viseme(phone)
    if vid == 0:
        continue   # skip silent phonemes inside a word
    events.append(VisemeEvent(vid, int(offset_ms * MS_TO_TICKS)))
```

### Server-side verified output

**"Hello"**:
```
   0.0 ms  v=0    (leading silence)
 397.5 ms  v=10   (AH — open mouth)
1141.2 ms  v=13   (OW — rounded mouth)
1587.5 ms  v=0    (sentence end)
duration: 1608 ms
```

**"Hello, I am your avatar. How are you doing today?"**:
```
   0.0  v=0       932.0 v=10    1972.1 v=2     2762.5 v=0     3575.0 v=4
 233.1 v=13      1131.7 v=1     2124.6 v=13    2827.5 v=13    3650.0 v=14
                 1264.8 v=12    2332.6 v=4     3000.0 v=10    3837.5 v=12
                 1385.9 v=13    2415.8 v=10    3172.5 v=9     4025.0 v=8
                 1612.8 v=9     2623.8 v=9     3287.5 v=12    4150.0 v=4
                 1764.1 v=10                   3387.5 v=14    4232.1 v=13
                                                               4437.5 v=4
                                                               4519.6 v=11
                                                               4725.0 v=0
duration: 4776 ms
```
Timeline is clean, sentence break at 2762–2827 (v0 then back to v13 for "How").

---

## Previously unresolved questions — status (2026-04-12)

### Q1. Stale HTTP server → **CONFIRMED & FIXED**
Three zombie server processes were running old code. After kill + restart,
server returns the correct 3-event timeline.

### Q2. Stale scene-serialized values → **CONFIRMED & FIXED**
Scene had Attempt 2 values (`smoothTime=0.08`, `lookAheadMs=150`,
`smoothAdvanceMs=90`). Updated to match code defaults (`0.03`, `80`, `100`)
and saved.

### Q3. Second lip-sync component → **Ruled out**
Only one `LipSyncBase` exists in the scene (`AnimClipLipSync` on `Avatar`).
`AzureSpeechManager.lipSyncController` correctly points to it.

### Q4. WAV duration drift → **Ruled out**
WAV sample count gives `1608.0 ms`, matching `duration_ms=1608.0` exactly.
No MP3 priming drift (server returns raw PCM WAV, not MP3-decoded).

### Q5. Wrong scheduler path → **Ruled out**
Direct call confirms `schedule_sentences()` is taken for edge-tts and
produces 3 events with `vid == 0` skip active.

### Q6. Viseme 0 rest pose — **Not yet verified**
Game-view screenshots show the mouth appears slightly open even after
audio ends and SmoothDamp should have decayed to the rest pose. This
could be the FBX frame 0 pose being not perfectly neutral, or it could
be normal for this MetaHuman model. Worth checking if lip-sync quality
still doesn't look right after the stale-state fix.

### Q7. Close-out window lag → **FIXED (Attempt 8)**
The `closeOutMs` window was anchored at `nextMs - closeOutMs` (the tail
of the gap) rather than at `curMs` (the head). For a last phoneme at 500ms
with a silence event at 1000ms, the mouth held the last shape from 500ms
to 850ms (350ms of hold while audio was already silent) before beginning
to close. Fixed: window now starts at `curMs` so closing begins immediately.

### Q8. Validator mid-playback screenshot → **FIXED (Attempt 8)**
`LipSyncValidator` used `_audioSource.time > _clipLength * 0.4f` which
never fired for streaming clips in Unity 6 (audioSource.time stays 0).
Mid-playback screenshot was silently skipped on every run. Fixed to use
wall-clock elapsed from audio-start.

---

## Diagnostic commands that work

### Dump viseme timeline for any phrase
```bash
.venv/Scripts/python -c "
from sound_engine.speech_synthesizer import SpeechSynthesizer
r = SpeechSynthesizer(timing_mode='enhanced').speak_text('Hello')
print(f'duration: {r.duration_ms:.1f} ms')
for e in r.viseme_events:
    print(f'{e.audio_offset/10000:7.1f} ms  v={e.viseme_id}')
"
```

### Phonemize a word
```bash
.venv/Scripts/python -c "
from sound_engine.phonemizer.phonemizer import Phonemizer
from sound_engine.viseme.arpabet_to_viseme import phoneme_to_viseme
for w in ['Hello', 'avatar', 'today']:
    phones = Phonemizer().phonemize_word_list([w])
    for word, ph in phones:
        vids = [phoneme_to_viseme(p) for p in ph]
        print(f'{word}: {list(zip(ph, vids))}')
"
```

### HTTP test (simulates what Unity sends)
```bash
curl -s -X POST http://127.0.0.1:5123/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello"}' | python -c "import json,sys; d=json.load(sys.stdin); print(f'duration: {d[\"duration_ms\"]:.1f} ms'); [print(f'{e[\"time_ms\"]:7.1f} ms  v={e[\"viseme_id\"]}') for e in d['viseme_events']]"
```

### Unity debug log
Set `AnimClipLipSync.debugLog = true` in the Inspector. Every 1 second
Update() logs: `t={elapsedMs}ms topViseme={id}(w={weight}) playing={bool}`.

### Self-validation (automated pass/fail from outside Unity)
From the repo root, with Unity already in play mode (e.g. TestSpeak has
just fired a phrase):
```bash
printf 'execute LipSyncValidator.Run' > agent_request.txt
# wait ~3 s for the clip to finish + 500 ms
cat lipsync_validation.txt
```
Report includes: per-100ms diagnostics, 3 screenshots under
`unity/aivatar/Assets/Screenshots/`, and a verdict block
(`Multiple visemes animated: PASS/FAIL`, `Mouth closed after audio: PASS/FAIL`).

### Drop-in diagnostic on AnimClipLipSync
`AnimClipLipSync.GetDiagnostics()` returns a single-line snapshot of
runtime state (`playing`, `audioMs`, `wallMs`, `frame`, `topViseme`,
`topWeight`, `lastIdx`, `visemeCount`) — used by the validator, also
useful for ad-hoc `Debug.Log` probes.

---

## Tuning parameters (Inspector on AnimClipLipSync)

| Parameter | Current default | Tune range | Effect |
|-----------|-----------------|------------|--------|
| `smoothTime` | `0.03` | 0.01–0.08 | Lower = snappier / less smoothing tail; higher = smoother |
| `lookAheadMs` | `80` | 40–200 | Crossfade begins this many ms before next phoneme |
| `smoothAdvanceMs` | `40` | 0–300 | Shift entire timeline forward by this many ms to compensate for SmoothDamp rise + MP3 priming + DSP buffer. Was 100 until Attempt 7; realtime fallback has no inherent DSP latency so 100 was overshooting. |
| `audioLatencyMs` | `0` | -100..100 | Platform-specific extra offset on top of `smoothAdvanceMs` |

---

## What DOES work (confirmed)

- Server-side pipeline produces mathematically correct viseme events
  (verified by hand for "Hello", "Ma. Pa. Ba. Bop.", and a 9-word phrase)
- Bone animation is running (jaw rotates 40°→50.5° on strong vowels, confirmed in earlier debug logs)
- Animation clip source `viseme_animation.fbx` has the expected 15 viseme
  poses in the expected order at 30 fps
- Unity compiles without errors (only a pre-existing missing-script warning, unrelated)
- `AvatarChatUI` → `AzureSpeechManager` → `lipSyncController.Play()`
  wiring is verified and functional
- HTTP bridge: `POST /speak` returns the expected JSON structure

## Remaining concerns

- **Viseme 10 vs 13 visual distinctness**: verify that FBX frames 100 (v=10)
  and 130 (v=13) produce visually different mouth shapes. If they're too
  similar, the FBX poses need adjustment.
- **Viseme 0 rest pose**: game-view screenshots show the mouth may be
  slightly open even at rest. If this is noticeable, investigate whether
  `viseme_animation.fbx` frame 0 is a true closed-mouth neutral pose.
- **Tuning**: `smoothAdvanceMs=100` is higher than the rule-of-thumb
  `1.8 × smoothTime × 1000 = 54 ms`. If visemes fire audibly early,
  lower toward `54`.

## Lessons learned

1. **Always restart the Python server** after editing `sound_engine/` code.
   The `HTTPServer` imports modules once at startup — it does not hot-reload.
2. **Changing `.cs` field defaults does not update existing scene instances.**
   Unity serializes public field values into `.unity` files. To apply new
   defaults, either: (a) reset the component in the Inspector, (b) use
   `manage_components set_property` via MCP, or (c) delete and re-add the
   component.
3. **Viseme deduplication can hide mapping bugs.** If two phonemes in the
   same word map to the same viseme ID, the scheduler's consecutive-ID
   dedup collapses them into one event. This makes the mapping error
   invisible in the event count — you have to check whether the phonemes
   *should* be visually distinct.
4. **`Application.runInBackground` defaults to false.** Whenever the
   Unity Editor loses focus (e.g. MCP tools stealing focus, or any
   external automation driving the editor), the whole player loop
   freezes — `Update()`, `Time.time`, and `Time.frameCount` all stop.
   Audio continues via the OS mixer which makes it look like the game
   is running when it isn't. Any agent/headless workflow must set this
   to `true` in `Awake()`, not rely on the Player Settings checkbox.
5. **Unity 6 `AudioSource.time` / `timeSamples` can stay at 0 for
   runtime-built clips** (`AudioClip.Create` + `SetData` or streaming
   PCMReaderCallback). The clip plays correctly through the mixer, but
   the AudioSource time fields never advance. Always carry a
   `Time.realtimeSinceStartup` fallback for any animation driven off
   `AudioSource.time`, and use wall-clock elapsed > clip length for
   end-of-clip detection instead of `!audioSource.isPlaying`.
6. **Build a validator before iterating blind.** Three attempts were
   spent chasing symptoms that only a human looking at the viewport
   could confirm. `LipSyncValidator.cs` + three screenshots + the
   diagnostic snapshot converted the feedback loop from "user eyeballs
   the mouth" to "read `lipsync_validation.txt`", and the remaining
   two bugs (runInBackground, time-zero) were diagnosed in one pass.
7. **A passing validator is not a passing animation.** The validator
   checked "≥2 distinct visemes seen" and "mouth closed after audio",
   both of which passed in Attempt 6 while the animation still looked
   robotic. "Distinct visemes seen" doesn't catch "each viseme held
   statically for 700ms". Future validators should sample the weight
   curve and fail on long flat plateaus.
8. **The validator itself can be affected by the same Unity 6 `audioSource.time=0`
   bug.** `LipSyncValidator` used `_audioSource.time > clipLength * 0.4f` to
   trigger the mid-playback screenshot. Since streaming clips return time=0,
   the screenshot condition never fired and was silently skipped every run.
   Any code that measures audio progress — not just `AnimClipLipSync` — must
   use wall-clock elapsed from a stamped start time.
9. **`closeOutMs` window direction matters.** Anchoring the close-to-silence
   fade at the *end* of the gap (`nextMs - window`) rather than the *start*
   (`curMs + window`) causes the mouth to hold the last phoneme for most of the
   gap and only begin closing in the last 150ms. When the gap includes trailing
   WAV silence (common with edge-tts), audio ends before the close begins.
   Always anchor from the event that fired, not from the future event.
