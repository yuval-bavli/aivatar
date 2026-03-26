"""Delete jaw_openExtreme key at frame 30, then re-create via float API."""
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

# Delete the existing key at frame 30
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                if 'openExtreme' in ch.get_name():
                    keys = list(ch.get_keys())
                    for k in keys:
                        if k.get_time().frame_number.value == 30:
                            ch.remove_key(k)
                            out.append(f"Removed jaw_openExtreme key at frame 30")
                    break
            break

# Scrub to frame 30 (display rate)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30)

# Re-key via float API with value 1.0
lib.set_local_control_rig_float(level_seq, face_rig, "CTRL_C_jaw_openExtreme",
    unreal.FrameNumber(30 * TICKS), 1.0, time_unit=TR, set_key=True)
out.append("Re-keyed jaw_openExtreme=1.0 at frame 30")

# Verify via API
val = lib.get_local_control_rig_float(level_seq, face_rig, "CTRL_C_jaw_openExtreme",
    unreal.FrameNumber(30 * TICKS), time_unit=TR)
out.append(f"API readback: {val}")

# Verify via channel
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                if 'openExtreme' in ch.get_name():
                    keys = list(ch.get_keys())
                    for k in keys:
                        if k.get_time().frame_number.value == 30:
                            out.append(f"Channel readback: {k.get_value():.4f}")
                    break
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
