# 3D Model Problem — MetaHuman Import to Unity URP

## The Setup

We have a MetaHuman character created in Unreal Engine. We exported it via FBX files (body, head, hair, eyebrows) and imported those into this Unity URP project. The goal is to make the Unity render look as close as possible to the original Unreal MetaHuman.

Reference image: `unity_3d_model_improver/3d_model_desired.png`

## The 3 Problems

1. **Eyelashes are too thick and bold** — They render as dark chunky strips instead of delicate lashes.
2. **Eyebrows are missing or not visible** — The eyebrow mesh was disabled; attempts to bake them into the face texture haven't produced visible results.
3. **Hair looks polygon-like** — Flat, plasticky appearance compared to the natural-looking hair in the Unreal reference.

## What We Tried (and why it failed)

### Attempt 1: qwen3-vl:8b audit loop (~100 iterations)

An automated loop where a local vision model (qwen3-vl:8b via Ollama) compared Unity screenshots to the reference and suggested material property tweaks. Claude applied the tweaks via `mat_editor.py` (YAML regex editing), refreshed Unity, and repeated.

**Why it failed:** `mat_editor.py` could only change float/color values in the `.mat` YAML files. But the actual root causes required deeper changes:

- **Eyelash material** had `_AlphaClip: 0` (alpha clipping disabled!) and ALL shader keywords (`_ALPHATEST_ON`, `_SURFACE_TYPE_TRANSPARENT`) were in `m_InvalidKeywords` instead of `m_ValidKeywords`. No amount of `_Cutoff` value tweaking matters when alpha clipping isn't even enabled — the shader ignores the cutoff entirely.
- **Hair material** had `_Smoothness: 0.95` (nearly glass-like reflectivity), making it look like plastic. The 8B vision model never identified this specific property as the issue — it kept suggesting color changes instead.
- **Eyebrow baking** went through 7+ iterations of C# bake scripts (BakeEyebrows1-7), each adjusting strength/thickness/color, but the baked results were either too dark or invisible. The eyebrow mesh renderer was disabled so the Eyebrows.mat wasn't being used at all.

### Attempt 2: Claude as sole judge/consultant

Tried having Claude Code visually judge the screenshots and suggest fixes without an external vision model. This also didn't produce meaningful improvements — Claude's visual judgment isn't reliable enough for subtle 3D render comparisons.

## Current Approach (3 sequential strategies)

After analyzing the root causes, we built 3 new approaches that the `3d-model-improver` skill tries sequentially:

1. **C# Material Fixer** (`metahuman_fixer.py`) — Generates C# Editor scripts that use Unity's `Material` API to programmatically set shader keywords, render queues, alpha clipping, surface types. This is what YAML editing couldn't do. Max 10 iterations.

2. **Texture Surgery** (`texture_editor.py`) — Direct pixel-level manipulation via Pillow: thin eyelash alpha channel with power curves, paint eyebrows using bezier curves with hair strokes, adjust hair texture contrast. Max 15 iterations.

3. **Upgraded AI** (`audit.py --mode upgraded`) — Uses qwen2.5-vl:32b (4x larger model) with full material property dumps sent alongside screenshots. The enhanced `mat_editor.py` can now apply keyword and render queue changes. Max 60 iterations.

Each approach runs for its iteration limit, then compares first vs last screenshot. If no progress (`PROGRESS: NO`), it switches to the next approach automatically via `approach_tracker.py`.

## Key Technical Details

- Materials are in `unity/aivatar/Assets/Models/Avatar/Materials/`
- The eyelash material uses a different shader GUID than hair/eyebrows
- Eye materials are already fixed (custom bake pipeline) — do NOT touch
- The Unity agent bridge (`CaptureScreenshot.cs`) enables file-based communication for screenshots, refresh, and script execution
- All Python tools are in `unity_3d_model_improver/` and run via `.venv/Scripts/python.exe`
- Setup: `bash unity_3d_model_improver/setup.sh`
