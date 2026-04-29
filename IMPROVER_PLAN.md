# MetaHuman → Unity Improver — Recoverable Spec

> The original implementation lived in `unity_3d_model_improver/` and was driven by a `3d-model-improver` Claude skill. The implementation has been removed; this document is the recipe for re-building it when the avatar needs another visual-quality pass.

## Goal

Take a MetaHuman exported from Unreal (FBX: body, head, hair, eyebrows) and converge the Unity URP render toward the original Unreal look. A reference image is preserved at `docs/3d_model_desired.png`.

## Known visual issues

1. **Eyelashes too thick/bold** — render as dark chunky strips instead of delicate lashes.
2. **Eyebrows missing or invisible** — eyebrow mesh disabled; bake-into-face-texture attempts produced no visible result.
3. **Hair looks plastic/polygon-like** — flat, glassy reflectivity vs. natural-looking Unreal hair.

Eye materials are **already fixed** (custom bake pipeline). Do **not** touch them.

## Why the naive YAML-edit loop failed

A vision model (qwen3-vl:8b) compared screenshots to the reference and Claude tweaked `.mat` YAML floats/colors via a `mat_editor.py` module. After ~100 iterations it never converged because:

- **Eyelash material** had `_AlphaClip: 0` and the relevant shader keywords (`_ALPHATEST_ON`, `_SURFACE_TYPE_TRANSPARENT`) sat in `m_InvalidKeywords` rather than `m_ValidKeywords`. The shader ignores `_Cutoff` until alpha clipping is actually enabled — a YAML float edit can never reach it.
- **Hair material** had `_Smoothness: 0.95` (near-glass). The 8B vision model never identified this property; it fixated on color tweaks.
- **Eyebrow mesh renderer was disabled**, so `Eyebrows.mat` wasn't being rendered at all. Bake scripts adjusted thickness/colour but nothing showed up.

Lesson: shader keywords, render queues, surface types, alpha clipping, blend/cull modes can only be set through Unity's `Material` API (`Material.EnableKeyword`, `Material.renderQueue`, etc.) — YAML tweaking is insufficient.

## Three-approach strategy

The skill cycled through approaches in order, switching when first-vs-last screenshot showed `PROGRESS: NO` for the iteration budget.

| # | Approach | Max iterations | Tool |
|---|----------|----------------|------|
| 1 | **C# Material Fixer** (deterministic) | 10 | Generate a one-shot C# Editor script that uses Unity's `Material` API to set keywords, render queues, surface types, `_AlphaClip`, blend/cull modes for the eyelash, hair, and eyebrow materials. Each generated class gets a unique name (`MetaHumanFixerN`) via a counter file to avoid Unity domain-reload conflicts. |
| 2 | **Texture Surgery** (Pillow) | 15 | Edit the texture PNGs directly: thin the eyelash alpha channel via power curves + Gaussian blur; paint eyebrows onto the face base-color texture (bezier curves with per-stroke variation); rebalance hair texture contrast/brightness. Backup each texture to `tex_backups/<name>_<timestamp>.png` before writing. |
| 3 | **Upgraded AI vision audit** | 60 | Run `qwen2.5-vl:32b` (4× larger than 8B) and pass *full material property dumps* in the prompt alongside before/after screenshots. The enhanced editor must be able to apply keyword + render-queue changes, not just floats/colors. |

A small `approach_tracker` persists `(current_approach_index, iteration_count, first_screenshot, last_screenshot, history)` to a JSON file so the loop survives conversation restarts.

## State machine

```
loop:
    state = load(approach_state.json)
    approach = APPROACHES[state.current_approach_index]
    if state.iteration_count == 0:
        state.first_screenshot = capture()
    apply(approach)
    state.last_screenshot = capture()
    state.iteration_count += 1
    if state.iteration_count >= approach.max_iterations:
        progress = compare(state.first_screenshot, state.last_screenshot)
        if progress == "NO":
            state.current_approach_index += 1
            state.iteration_count = 0
            state.first_screenshot = None
        save(state)
```

## Unity ↔ Python bridge

File-based protocol (no MCP dependency required):

- Python writes a command to `unity/aivatar/agent_request.txt`.
- A small Unity Editor script polls for the file and writes `unity/aivatar/agent_result.txt`.

Three commands sufficed:
- `screenshot` — captures main camera; returns the saved PNG path
- `refresh` — `AssetDatabase.Refresh()` + waits for compilation; returns `ready`
- `execute ClassName.Method` — calls a static C# method, returns its string result

If/when re-building, the equivalent Unity MCP tools (`mcp__unity__refresh_unity`, `mcp__unity__manage_scene`, `mcp__unity__execute_menu_item`, `mcp__unity__manage_components`) can replace the file bridge and the `CaptureScreenshot.cs` Editor script.

## Material/texture locations

- Materials: `unity/aivatar/Assets/Models/Avatar/Materials/`
- Textures: `unity/aivatar/Assets/Models/Avatar/Textures/`
- Editable materials whitelist: `Eyebrows`, `haircut`, `MI_Face_EyelashesHiLODs`, `M_Hide`, `M_Hide_6`
- Eyelash uses a **different shader GUID** from hair/eyebrows — handle separately.

## Calibration starting points (from the last successful run)

```
eyelash_cutoff   = 0.45
eyelash_alpha    = 0.35
eyelash_color    = (0.12, 0.08, 0.06)
hair_smoothness  = 0.45
hair_cutoff      = 0.15
hair_color       = (0.22, 0.16, 0.11)
eyebrow_cutoff   = 0.30
enable_eyebrow_mesh = true
```

## Re-implementation notes

- **Backups are mandatory.** Each material/texture write should snapshot the original to `mat_backups/` / `tex_backups/` (timestamped) before overwriting — earlier attempts repeatedly corrupted state without an undo path.
- **Generate uniquely-named C# classes per iteration** to avoid Unity domain reload caching old code.
- The vision-model audit should respond with a strict format (`PROGRESS: YES|NO`, `ISSUES FOUND` block) so the controller can parse it deterministically. Free-form chat output stalls the loop.
- The `3d-model-improver` Claude skill at `~/.claude/skills/` referenced this directory; if rebuilding, also restore (or rewrite) that skill, otherwise delete it to avoid dead pointers.
