"""
Fix TH viseme using ONLY float controls (which work correctly).
Use CTRL_C_jaw_openExtreme to open the jaw instead of patching jaw.Y channel.
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
frame = 30

# Scrub to TH frame
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)

# Use jaw_openExtreme (float, works correctly) to open jaw
try:
    lib.set_local_control_rig_float(level_seq, face_rig, "CTRL_C_jaw_openExtreme",
        unreal.FrameNumber(frame * TICKS), 0.5, time_unit=TR, set_key=True)
    out.append("Keyed CTRL_C_jaw_openExtreme=0.5 at frame 30")
except Exception as e:
    out.append(f"jaw_openExtreme error: {e}")

out.append(f"Scrubbed to frame {frame} (TH)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
