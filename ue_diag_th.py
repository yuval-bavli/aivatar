"""Diagnose why frame 30 shows rest pose. Check key positions and read control values."""
import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

rigs = lib.get_control_rigs(level_seq)
face_rig = None
for proxy in rigs:
    cr = proxy.control_rig
    if "Face" in cr.get_name():
        face_rig = cr
        break

TICKS = 800
TR = unreal.MovieSceneTimeUnit.TICK_RESOLUTION

# Read back current values at different frames using the GET API
for frame in [0, 10, 30]:
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)
    out.append(f"\n=== Frame {frame} ===")

    # Read jaw_openExtreme value
    try:
        val = lib.get_local_control_rig_float(level_seq, face_rig, "CTRL_C_jaw_openExtreme",
            unreal.FrameNumber(frame * TICKS), time_unit=TR)
        out.append(f"  jaw_openExtreme: {val}")
    except Exception as e:
        out.append(f"  jaw_openExtreme: ERROR {e}")

    # Read tongue_inOut
    try:
        val = lib.get_local_control_rig_float(level_seq, face_rig, "CTRL_C_tongue_inOut",
            unreal.FrameNumber(frame * TICKS), time_unit=TR)
        out.append(f"  tongue_inOut: {val}")
    except Exception as e:
        out.append(f"  tongue_inOut: ERROR {e}")

    # Read pressU
    try:
        val = lib.get_local_control_rig_float(level_seq, face_rig, "CTRL_L_mouth_pressU",
            unreal.FrameNumber(frame * TICKS), time_unit=TR)
        out.append(f"  L_mouth_pressU: {val}")
    except Exception as e:
        out.append(f"  L_mouth_pressU: ERROR {e}")

    # Read jaw vec2d
    try:
        val = lib.get_local_control_rig_vector2d(level_seq, face_rig, "CTRL_C_jaw",
            unreal.FrameNumber(frame * TICKS), time_unit=TR)
        out.append(f"  jaw vec2d: {val}")
    except Exception as e:
        out.append(f"  jaw vec2d: ERROR {e}")

# Also check the raw channel key tick values for jaw_openExtreme
out.append("\n=== Raw channel keys ===")
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                name = ch.get_name()
                if 'openExtreme' in name or 'tongue_inOut' in name or 'pressU' in name.split('_')[-1:]:
                    keys = list(ch.get_keys())
                    if keys:
                        out.append(f"  {name}:")
                        for k in keys:
                            out.append(f"    tick={k.get_time().frame_number.value} val={k.get_value():.4f}")
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
