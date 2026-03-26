"""
Key jaw_openExtreme at frame 30 by scrubbing AWAY from frame 30 first.
Theory: the API captures the rig's current evaluation, so scrubbing to
the target frame causes it to capture the current (zero) value instead
of the requested value.
"""
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

# Remove existing key at frame 30
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                if 'openExtreme' in ch.get_name():
                    for k in list(ch.get_keys()):
                        if k.get_time().frame_number.value == 30:
                            ch.remove_key(k)
                            out.append("Removed old key at frame 30")
                    break
            break

# Scrub FAR AWAY from frame 30 (out of bounds or to frame 0)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30 * TICKS)  # way out of bounds
out.append(f"Scrubbed to {30 * TICKS} (out of bounds)")

# Now key at frame 30 with value 1.0
lib.set_local_control_rig_float(level_seq, face_rig, "CTRL_C_jaw_openExtreme",
    unreal.FrameNumber(30 * TICKS), 1.0, time_unit=TR, set_key=True)
out.append("Keyed jaw_openExtreme=1.0 at frame 30")

# Scrub back to frame 30 to check
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30)

# Verify
val = lib.get_local_control_rig_float(level_seq, face_rig, "CTRL_C_jaw_openExtreme",
    unreal.FrameNumber(30 * TICKS), time_unit=TR)
out.append(f"API readback at frame 30: {val}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
