"""Test a single set_local_control_rig_float call and check result."""
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

TICKS = 800
TR = unreal.MovieSceneTimeUnit.TICK_RESOLUTION

# Try to key a single control
ctrl_name = "CTRL_L_mouth_pressU"
frame = 10
value = 0.8

# Count keys before
before_keys = 0
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                if 'pressU' in ch.get_name() and 'CTRL_L' in ch.get_name():
                    before_keys = len(list(ch.get_keys()))
                    out.append(f"Channel: {ch.get_name()}, keys before: {before_keys}")
            break

# Try different approaches
# Approach 1: Original pattern
try:
    lib.set_local_control_rig_float(level_seq, face_rig, ctrl_name,
        unreal.FrameNumber(frame * TICKS), float(value), time_unit=TR, set_key=True)
    out.append(f"Approach 1 (tick resolution): No error")
except Exception as e:
    out.append(f"Approach 1 failed: {e}")

# Approach 2: Display rate
try:
    lib.set_local_control_rig_float(level_seq, face_rig, ctrl_name,
        unreal.FrameNumber(frame), float(value),
        time_unit=unreal.MovieSceneTimeUnit.DISPLAY_RATE, set_key=True)
    out.append(f"Approach 2 (display rate): No error")
except Exception as e:
    out.append(f"Approach 2 failed: {e}")

# Count keys after
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                if 'pressU' in ch.get_name() and 'CTRL_L' in ch.get_name():
                    after_keys = len(list(ch.get_keys()))
                    out.append(f"Keys after: {after_keys}")
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
