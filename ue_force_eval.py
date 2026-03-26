"""
Check if sequencer is evaluating and try to force evaluation.
The track recreation may have broken the evaluation link.
"""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
lib = unreal.ControlRigSequencerLibrary

# Check if sequence is locked/active
try:
    is_locked = unreal.LevelSequenceEditorBlueprintLibrary.is_level_sequence_locked()
    out.append(f"Sequence locked: {is_locked}")
except Exception as e:
    out.append(f"is_locked: {e}")

# Try to lock (enable evaluation)
try:
    unreal.LevelSequenceEditorBlueprintLibrary.set_lock_level_sequence(True)
    out.append("Locked sequence")
except Exception as e:
    out.append(f"set_lock: {e}")

# Check playing state
try:
    is_playing = unreal.LevelSequenceEditorBlueprintLibrary.is_playing()
    out.append(f"Is playing: {is_playing}")
except Exception as e:
    out.append(f"is_playing: {e}")

# Try to force refresh by playing briefly
try:
    unreal.LevelSequenceEditorBlueprintLibrary.play()
    import time
    # Can't sleep in UE python, just play and stop
    unreal.LevelSequenceEditorBlueprintLibrary.pause()
    out.append("Played and paused")
except Exception as e:
    out.append(f"play/pause: {e}")

# Force scrub to PP (frame 10) to test evaluation
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(10 * 800)

# Read the pressU value via the rig API
rigs = lib.get_control_rigs(level_seq)
face_rig = None
for proxy in rigs:
    cr = proxy.control_rig
    if "Face" in cr.get_name():
        face_rig = cr
        break

# Check if the control rig has the expected value at frame 10
try:
    val = lib.get_local_control_rig_float(level_seq, face_rig, "CTRL_L_mouth_pressU",
        unreal.FrameNumber(10 * 800), time_unit=unreal.MovieSceneTimeUnit.TICK_RESOLUTION)
    out.append(f"\npressU at frame 10 (from API): {val}")
except Exception as e:
    out.append(f"pressU read: {e}")

# Check face binding validity
for b in level_seq.get_bindings():
    bname = b.get_display_name()
    bound = b.get_bound_objects()
    out.append(f"\nBinding '{bname}': {len(bound)} bound objects")
    for obj in bound:
        out.append(f"  {obj.get_name()} ({type(obj).__name__})")

out.append(f"\nScrubbed to frame 10 (PP)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
