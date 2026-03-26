"""Test if setting rig values WITHOUT set_key drives the visual."""
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

out.append(f"Face rig: {face_rig.get_name()}")

# Scrub to frame 0 first
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
out.append("Scrubbed to frame 0")

# Try setting jaw value WITHOUT set_key (just drive the rig)
try:
    lib.set_local_control_rig_float(level_seq, face_rig, "CTRL_C_jaw_openExtreme",
        unreal.FrameNumber(0), 1.0,
        time_unit=unreal.MovieSceneTimeUnit.DISPLAY_RATE, set_key=False)
    out.append("set_local_control_rig_float(openExtreme=1.0, set_key=False): OK")
except Exception as e:
    out.append(f"Error: {e}")

# Try vec2d
try:
    lib.set_local_control_rig_vector2d(level_seq, face_rig, "CTRL_C_jaw",
        unreal.FrameNumber(0), unreal.Vector2D(0, -2.0),
        time_unit=unreal.MovieSceneTimeUnit.DISPLAY_RATE, set_key=False)
    out.append("set_local_control_rig_vector2d(jaw=(0,-2), set_key=False): OK")
except Exception as e:
    out.append(f"Vec2d error: {e}")

# Also try pressU to test a known-working float control
try:
    lib.set_local_control_rig_float(level_seq, face_rig, "CTRL_L_mouth_pressU",
        unreal.FrameNumber(0), 1.0,
        time_unit=unreal.MovieSceneTimeUnit.DISPLAY_RATE, set_key=False)
    out.append("set_local_control_rig_float(pressU=1.0, set_key=False): OK")
except Exception as e:
    out.append(f"pressU error: {e}")

out.append("\nCheck viewport — jaw should be open and lips pressed at frame 0")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
