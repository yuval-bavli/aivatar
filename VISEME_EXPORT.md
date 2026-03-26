# Viseme Animation Export — Status & Context

## What was done (2026-03-21)

15 Azure viseme poses keyed into the MetaHuman `Face_ControlBoard_CtrlRig` in Unreal Engine 5.7, then exported as FBX for Unity import.

### Viseme mapping (frame → viseme)

| Frame | ID  | Name | Description |
|-------|-----|------|-------------|
| 0     | 0   | sil  | Silent/rest (all zero) |
| 10    | 1   | PP   | Lips pressed (B/M/P) |
| 20    | 2   | FF   | Lower lip under teeth (F/V) |
| 30    | 3   | TH   | Tongue between teeth (TH) |
| 40    | 4   | DD   | Tongue behind teeth (D/T/N) |
| 50    | 5   | kk   | Back tongue (K/G) |
| 60    | 6   | CH   | Rounded lips (SH/CH/J) |
| 70    | 7   | SS   | Teeth together spread (S/Z) |
| 80    | 8   | nn   | Tongue up relaxed (N/NG) |
| 90    | 9   | RR   | Slightly rounded (R) |
| 100   | 10  | aa   | Wide open (A) |
| 110   | 11  | E    | Mid open spread (E) |
| 120   | 12  | ih   | Narrow spread (I) |
| 130   | 13  | oh   | Round open (O) |
| 140   | 14  | ou   | Tight pucker (U/OO) |

Spacing: 10 frames apart at 30fps (~0.33s each), total 150 frames (~5s).

### Output files

- `viseme_animation.fbx` (48MB) — FBX export of the full level sequence including face rig
- UE asset `/Game/Aivatar/VisemeAnimation` — baked AnimSequence inside the project
- UE asset `/Game/Aivatar/VisemePoses` — older asset from previous attempts (may be stale)

### UE project details

- **Project**: `ModelProject2` at `c:/Users/yuval/OneDrive/Documents/Unreal Projects/ModelProject2`
- **Level sequence**: `FaceExport` at `/Game/MetaHumans/model4/Face/FaceExport`
- **MetaHuman**: model4 — bindings: `Face` (face rig), `Body` (body rig), `BP_model4`
- **Face skeleton**: `Face_Archetype_Skeleton`

### Critical API lessons

1. `MovieSceneControlRigParameterSection.add_scalar_parameter_key()` does **NOT** drive the control rig. It creates orphan parameter curves.

2. **MUST scrub before keying**: Call `set_current_time(frame * 800)` before each `set_local_control_rig_*` call. The API keys at the scrub position.

3. **Use TICK_RESOLUTION, not DISPLAY_RATE**: Pass `FrameNumber(frame * 800)` with `time_unit=TICK_RESOLUTION`.

4. **`set_local_control_rig_vector2d` IGNORES the value parameter** — it creates keys at the correct positions but always writes (0,0). You must fix values directly on channel keys after creation using `key.set_value(float_val)`. The float API (`set_local_control_rig_float`) works correctly.

```python
TICKS = 800
TR = unreal.MovieSceneTimeUnit.TICK_RESOLUTION

# Scrub FIRST
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)

# Float controls work correctly
lib.set_local_control_rig_float(
    level_seq, face_rig, "CTRL_C_jaw_openExtreme",
    unreal.FrameNumber(frame * TICKS), 1.0,
    time_unit=TR, set_key=True)

# Vector2D controls: create key (value ignored), then fix on channel
lib.set_local_control_rig_vector2d(
    level_seq, face_rig, "CTRL_C_jaw",
    unreal.FrameNumber(frame * TICKS), unreal.Vector2D(0, -0.7),
    time_unit=TR, set_key=True)
# Then find jaw.Y channel and do: key.set_value(-0.7)
```

To get `face_rig`: `lib.get_control_rigs(level_seq)` returns `ControlRigSequencerBindingProxy` — access `.control_rig` for the actual `ControlRig`.

### Key scripts

- `ue_remote.py` — sends Python to UE via HTTP Remote Control API (port 30010)
- `ue_viseme_key_final.py` — the working script that keys all 15 visemes (scrub-then-key pattern)
- `ue_export_visemes.py` — exports FBX + bakes AnimSequence

### Next steps for Unity

1. Import `viseme_animation.fbx` into Unity
2. The FBX contains bone animation baked from the control rig at each viseme frame
3. In Unity, extract individual viseme poses from the animation clip (frames 0, 10, 20, ... 140)
4. Wire into the existing `ProLipSync` / `VisemeMapping` system
