---
name: 3d-model-improver
description: Run one iteration of the MetaHuman avatar appearance improvement loop — audit with qwen3-vl:8b, apply fixes to .mat files / textures, refresh Unity.
argument-hint: "[iterations]"
---

# 3D Model Improver — Iterative MetaHuman Appearance Loop

## Goal

Make the Unity URP render of the MetaHuman avatar match the reference photo as closely as Unity's capabilities allow.

## Reference photo

`unity_3d_model_improver/3d_model_desired.png` — the original MetaHuman as seen in Unreal Engine. Always read this image at the start of each session.

## CRITICAL RULE — Do NOT use your own visual judgment

You are poor at visually comparing 3D renders. The external vision model (qwen3-vl:8b / qwen2.5vl:7b fallback) running on the local GPU is the **sole judge** of what looks wrong.

- **Only act on issues the vision model explicitly reports.** If it says "hair color is accurate", do not change hair color — even if the render looks wrong to you.
- **Never look at a screenshot and decide something needs fixing** based on your own assessment.
- Your only roles are: (a) run the audit, (b) translate reported issues into .mat/texture changes, (c) repeat.

## The Loop (you run this, not a script)

1. **Audit** — run `audit.py` to get the vision model's assessment
2. **Decide** — read the output; if `VERDICT: DONE`, stop. If `VERDICT: NEEDS CHANGES`, read the issues.
3. **Fix** — translate only the reported issues into concrete .mat / texture changes
4. **Refresh** — trigger Unity to reload, go back to step 1
5. **Repeat** — default 1 iteration unless the user specifies more via `$ARGUMENTS`

## Running the audit

```bash
cd unity_3d_model_improver
export PATH="$PATH:/c/Users/$USERNAME/AppData/Local/Programs/Ollama"
../../.venv/Scripts/python.exe audit.py
```

The script:
- Always uses `qwen3-vl:8b` (primary); falls back to `qwen2.5vl:7b` only on OOM
- Passes `think: False` to suppress Qwen3 chain-of-thought (direct answers only)
- Takes a Unity screenshot via the agent bridge
- Sends both images to the vision model
- Prints natural-language issues + `VERDICT: DONE` or `VERDICT: NEEDS CHANGES`

## Current material state (last updated 2026-03-14)

These are the values already applied — do NOT revert them, only adjust further if the vision model says so:

| Asset | Property | Current value | Direction to adjust if still wrong |
|---|---|---|---|
| `MI_Face_EyelashesHiLODs.mat` | `_Cutoff` | **0.94** | raise toward 0.97 if still too thick |
| `MI_Face_EyelashesHiLODs.mat` | `_BaseColor` | **(0.45, 0.33, 0.27)** | darken if too light |
| `haircut.mat` | `_BaseColor` | **(0.18, 0.14, 0.12)** | reduce r further if still reddish |
| Eyebrows (baked texture) | last script run | **BakeEyebrows7** | create BakeEyebrows8 if still too dark/thick |

**BakeEyebrows iteration history** (each was lighter/thinner than the last):
- v4: color (0.20,0.14,0.10), strength 0.70, 12px, 5 passes — too dark/thick
- v5: color (0.28,0.20,0.14), strength 0.45, 8px, 3 passes — still too dark
- v6: color (0.35,0.25,0.17), strength 0.28, 6px, 2 passes — still too dark
- v7: color (0.42,0.32,0.22), strength 0.16, 4px, 1 pass — **current**

## Applying fixes

### Editable .mat files (direct YAML edit)

All in `unity/aivatar/Assets/Models/Avatar/Materials/`:

| File | What it controls |
|------|-----------------|
| `Eyebrows.mat` | Eyebrow card mesh material (mesh is **disabled** — baked into face texture instead) |
| `haircut.mat` | Hair color, cutoff, smoothness |
| `MI_Face_EyelashesHiLODs.mat` | Eyelash darkness, thickness (`_Cutoff` higher = thinner) |
| `MID_M_DG_bodyShapeB_Shirt_70.mat` | Shirt color |
| `MID_M_DG_bodyShapeB_Short_71.mat` | Shorts color |
| `M_Hide.mat` / `M_Hide_6.mat` | Scalp backing under hair |

Key YAML properties to edit:
- `_BaseColor: {r: X, g: X, b: X, a: 1}` — also update the matching `_Color` line
- `_Cutoff: X` — alpha cutoff (0–1)
- `_Smoothness: X` — surface glossiness (0–1)

### Eyebrows (baked into face texture)

The eyebrow mesh is **disabled**. Eyebrows are painted onto:
`unity/aivatar/Assets/Models/Avatar/Textures/T_Head_BC_VT_Brows.png`

Latest bake script: `BakeEyebrows7.cs` (ultra-light: 4px, strength 0.16, single pass, color 0.42/0.32/0.22).
To re-bake with different settings, create a new `BakeEyebrowsN.cs`, then:
```bash
# refresh so Unity compiles it, then execute
```

UV mapping (for direct pixel edits):
- Right eyebrow (viewer's left): pixels ≈ (654–737, 1291–1532)
- Left eyebrow (viewer's right): pixels ≈ (1328–1431, 1295–1589)

### Triggering Unity refresh after edits

Use the Python helper (preferred, run from repo root):
```bash
/c/Users/yuval/src/aivatar/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'unity_3d_model_improver')
import unity_bridge
unity_bridge.refresh()
print(unity_bridge.execute('BakeEyebrowsN.Run'))
"
```

Or via the agent bridge directly (see `unity-run` skill for protocol).

## DO NOT TOUCH — Eyes

The eye materials are already fixed via a custom bake pipeline. Do not modify:
- `MI_EyeR_Baked`, `MI_EyeL_Baked` — baked sclera+iris composites
- `MI_Face_EyeShell` — cornea overlay (nearly invisible, high smoothness)
- `MI_Face_LacrimalFluid` — tear fluid

## Known constraints (set expectations correctly)

- **Hair polygon look** — inherent to hair cards; no material fix can solve this
- **Eyebrow subtlety** — baked arcs look faint at render distance; increase `strength`/`thickness` in the bake script if too faint
- **Scalp gaps** — normal for hair cards; dark M_Hide backing minimizes visibility

## Python helpers (optional, for complex edits)

- `unity_3d_model_improver/mat_editor.py` — `apply_change(mat_name, prop, value)`
- `unity_3d_model_improver/unity_bridge.py` — `screenshot()`, `refresh()`, `execute()`

Run with: `../../.venv/Scripts/python.exe`
