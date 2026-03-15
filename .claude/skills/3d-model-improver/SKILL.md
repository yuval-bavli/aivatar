---
name: 3d-model-improver
description: Run the MetaHuman avatar improvement loop — cycles through 3 approaches (C# fixer, texture surgery, upgraded AI), auto-switching when one fails.
argument-hint: "[iterations]"
---

# 3D Model Improver — Multi-Approach MetaHuman Improvement Loop

## Goal

Make the Unity URP render of the MetaHuman avatar match the reference photo as closely as Unity's capabilities allow. Three known problems to fix:

1. **Eyelashes** — too thick/bold compared to reference
2. **Eyebrows** — missing or not visible
3. **Hair** — looks polygon-like / overly glossy compared to reference

## Reference photo

`unity_3d_model_improver/3d_model_desired.png` — the original MetaHuman as seen in Unreal Engine. Read this image at the start of each session.

## CRITICAL RULE — Do NOT use your own visual judgment

The external vision model running on the local GPU is the **sole judge**. You tried being the judge before — it didn't work.

- **Only act on issues the vision model explicitly reports.**
- **Never look at a screenshot and decide something needs fixing** based on your own assessment.
- Your roles: (a) run the audit, (b) apply the approach's fix method, (c) repeat.

## Architecture — 3 Approaches (tried sequentially)

The system tries each approach for a limited number of iterations. After the limit, it compares the first screenshot to the last screenshot using the vision model. If `PROGRESS: NO`, it switches to the next approach.

### Approach 1: C# Material Fixer (deterministic) — max 10 iterations

**Why this should work:** The root cause of 100 failed iterations was that the old `mat_editor.py` could only edit float/color values in YAML. But the eyelash material had `_AlphaClip: 0` (disabled!) and ALL shader keywords in `m_InvalidKeywords`. No amount of `_Cutoff` tweaking matters when alpha clipping isn't enabled. This approach uses Unity's `Material` C# API to set keywords, render queues, surface types — things YAML editing can't do.

**How to run:**
```bash
cd unity_3d_model_improver
../../.venv/Scripts/python.exe metahuman_fixer.py [--eyelash-cutoff 0.45] [--hair-smoothness 0.45]
```

**What it does (one-shot):**
- Eyelash mat: Enables `_ALPHATEST_ON` keyword, sets `_AlphaClip=1`, `_Cutoff=0.45`, switches to URP/Lit shader, sets render queue 2450
- Hair mat: Reduces `_Smoothness` from 0.95 to 0.45, disables env reflections, sets proper color
- Eyebrow mesh: Re-enables the disabled eyebrow SkinnedMeshRenderer, fixes its material
- Scalp mats: Darkens M_Hide/M_Hide_6 to minimize visibility through hair cards
- Eyelash textures: Fixes import settings (alpha source, alpha-is-transparency)

**After running:** Audit with `audit.py`. If issues remain, re-run `metahuman_fixer.py` with adjusted parameters based on audit feedback (e.g., `--eyelash-cutoff 0.55` if still too thick).

### Approach 2: Texture Surgery (Pillow) — max 15 iterations

**Why this should work:** Some problems can't be fixed by material properties alone. If the eyelash texture itself has strands that are too thick, or eyebrows aren't visible in the baked face texture, you need pixel-level manipulation.

**How to run:**
```bash
cd unity_3d_model_improver
../../.venv/Scripts/python.exe texture_editor.py fix-all
# Or individually:
../../.venv/Scripts/python.exe texture_editor.py fix-eyelashes --thin-factor 0.5
../../.venv/Scripts/python.exe texture_editor.py fix-eyebrows --strength 0.35 --color 0.28,0.20,0.14
../../.venv/Scripts/python.exe texture_editor.py fix-hair --contrast 1.2
```

**What it does:**
- **Eyelash thinning:** Applies power curve to alpha channel making thin areas transparent. `--thin-factor 0.5` = half thickness. Lower = thinner.
- **Eyebrow painting:** Paints bezier-curve eyebrows with individual hair strokes onto `T_Head_BC_VT_Brows.png`. Parameters: `--strength` (blend opacity), `--color` (RGB 0-1).
- **Hair contrast:** Increases texture contrast to break the flat/polygon look.

**After editing textures:** Must trigger Unity refresh so it reimports them:
```bash
../../.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'unity_3d_model_improver')
import unity_bridge; unity_bridge.refresh()
"
```

### Approach 3: Upgraded AI (qwen2.5-vl:32b) + Full Material Context — max 60 iterations

**Why this should work:** The original qwen3-vl:8b is too small to reason about Unity material internals. The 32B model can see the full material property dumps alongside screenshots and give specific property+keyword fixes. The enhanced `mat_editor.py` can now apply keyword changes.

**How to run the audit:**
```bash
cd unity_3d_model_improver
export PATH="$PATH:/c/Users/$USERNAME/AppData/Local/Programs/Ollama"
../../.venv/Scripts/python.exe audit.py --mode upgraded
```

**Key difference from old approach:**
- Model is 4x larger (32B vs 8B) — much better visual reasoning
- The prompt includes ALL material properties (floats, colors, keywords, render queues)
- The AI can suggest keyword changes: `{"material": "X", "action": "enable_keyword", "keyword": "_ALPHATEST_ON"}`
- The enhanced `mat_editor.py` can apply these keyword changes via YAML manipulation

**Applying fixes from upgraded audit:**
The upgraded audit outputs JSON change instructions. Apply them:
```bash
../../.venv/Scripts/python.exe -c "
import sys, json; sys.path.insert(0, 'unity_3d_model_improver')
import mat_editor
changes = [...]  # paste the JSON changes from audit output
errors = mat_editor.apply_changes(changes)
if errors: print('ERRORS:', errors)
"
```

Then refresh Unity and re-audit.

## The Loop (you run this, not a script)

1. **Check state** — run `approach_tracker.py status` to see current approach and iteration count
2. **Apply the current approach's fix** (see above for each approach)
3. **Refresh Unity** — `unity_bridge.refresh()`
4. **Audit** — run `audit.py` (use `--mode upgraded` for approach 3)
5. **Track** — run `approach_tracker.py` to increment iteration and store screenshot
6. **Decide:**
   - If `VERDICT: DONE` → stop, you're done!
   - If `VERDICT: NEEDS CHANGES` and under iteration limit → go to step 2
   - If at iteration limit → run comparison, then `approach_tracker.py next` to switch

### Running the approach tracker

```bash
cd unity_3d_model_improver
../../.venv/Scripts/python.exe approach_tracker.py status     # Show current state
../../.venv/Scripts/python.exe approach_tracker.py reset      # Start fresh from approach 1
../../.venv/Scripts/python.exe approach_tracker.py next       # Switch to next approach
```

Programmatic usage (from Python):
```python
import approach_tracker
state = approach_tracker.get_state()
state = approach_tracker.increment_iteration(screenshot_path="/path/to/screenshot.png")
if state.should_switch:
    approach_tracker.switch_to_next_approach("No progress after N iterations")
```

### Running comparison (at end of each approach)

```bash
cd unity_3d_model_improver
../../.venv/Scripts/python.exe audit.py --compare /path/to/first.png /path/to/last.png --iterations 10
```

This outputs `PROGRESS: YES` or `PROGRESS: NO` to decide whether to continue or switch.

## Applying fixes — quick reference

### mat_editor.py (enhanced — supports keywords now)

```python
import mat_editor

# Float/color (same as before)
mat_editor.apply_change("haircut", "_Cutoff", 0.25)
mat_editor.apply_change("haircut", "_BaseColor", [0.22, 0.15, 0.1, 1.0])

# NEW: Keywords
mat_editor.apply_keyword_change("MI_Face_EyelashesHiLODs", "enable_keyword", "_ALPHATEST_ON")
mat_editor.apply_keyword_change("MI_Face_EyelashesHiLODs", "disable_keyword", "_SURFACE_TYPE_TRANSPARENT")

# NEW: Render queue
mat_editor.apply_render_queue("MI_Face_EyelashesHiLODs", 2450)

# Batch (supports all formats)
mat_editor.apply_changes([
    {"material": "haircut", "property": "_Smoothness", "value": 0.4},
    {"material": "MI_Face_EyelashesHiLODs", "action": "enable_keyword", "keyword": "_ALPHATEST_ON"},
    {"material": "MI_Face_EyelashesHiLODs", "action": "set_render_queue", "value": 2450},
])
```

### Unity refresh after edits

```bash
../../.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'unity_3d_model_improver')
import unity_bridge; unity_bridge.refresh()
"
```

### Executing C# Editor scripts

```bash
../../.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'unity_3d_model_improver')
import unity_bridge
unity_bridge.refresh()
print(unity_bridge.execute('ClassName.Run'))
"
```

## DO NOT TOUCH — Eyes

The eye materials are already fixed. Do not modify:
- `MI_EyeR_Baked`, `MI_EyeL_Baked` — baked sclera+iris composites
- `MI_Face_EyeShell` — cornea overlay
- `MI_Face_LacrimalFluid` — tear fluid

## Root cause analysis (why 100 iterations failed)

The old approach had three fundamental problems:

1. **mat_editor.py could only edit float/color YAML values** — it couldn't set shader keywords (`_ALPHATEST_ON`), change render queues, or enable alpha clipping. The eyelash material had `_AlphaClip: 0` and all keywords were `m_InvalidKeywords`. No amount of `_Cutoff` tweaking works when alpha clipping is disabled.

2. **qwen3-vl:8b is too small** to understand Unity material internals. It would say "make eyelashes thinner" but couldn't tell you that `_AlphaClip` needs to be 1 and `_ALPHATEST_ON` must be in `m_ValidKeywords`.

3. **Hair `_Smoothness` was 0.95** (nearly glass-like) making it look plastic/polygon-like, but the AI never identified this specific property as the issue.

## Python helpers

All in `unity_3d_model_improver/`:

| File | Purpose |
|------|---------|
| `metahuman_fixer.py` | Approach 1: Generates + executes C# Editor scripts for material fixes |
| `texture_editor.py` | Approach 2: Pillow-based texture manipulation |
| `audit.py` | Visual auditor (supports standard + upgraded modes) |
| `approach_tracker.py` | Tracks current approach, iteration count, screenshot comparison |
| `mat_editor.py` | YAML-based material editor (now supports keywords + render queues) |
| `unity_bridge.py` | Unity agent bridge (screenshot, refresh, execute) |
| `vram_manager.py` | GPU model selection |

Run with: `../../.venv/Scripts/python.exe`
