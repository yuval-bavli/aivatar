"""Increase jaw opening at TH (frame 30) using jaw_openExtreme float control."""
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
frame = 30

# Scrub to frame 30 (display rate!)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame)

# Increase jaw_openExtreme to 1.0 (max) at TH
lib.set_local_control_rig_float(level_seq, face_rig, "CTRL_C_jaw_openExtreme",
    unreal.FrameNumber(frame * TICKS), 1.0, time_unit=TR, set_key=True)
out.append("Keyed CTRL_C_jaw_openExtreme=1.0 at frame 30")

# Verify
val = lib.get_local_control_rig_float(level_seq, face_rig, "CTRL_C_jaw_openExtreme",
    unreal.FrameNumber(frame * TICKS), time_unit=TR)
out.append(f"Readback: {val}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
