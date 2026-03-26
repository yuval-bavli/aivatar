"""Test if set_key=True now creates keys after add_scalar_parameter_key registered params."""
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

# Count pressU keys before
before = 0
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            for ch in t.get_sections()[0].get_all_channels():
                if 'pressU' in ch.get_name() and 'CTRL_L' in ch.get_name():
                    before = ch.get_num_keys()
                    out.append(f"pressU keys before: {before}")
                    break
            break

# Try set_key=True
lib.set_local_control_rig_float(level_seq, face_rig, "CTRL_L_mouth_pressU",
    unreal.FrameNumber(5), 0.99,
    time_unit=unreal.MovieSceneTimeUnit.DISPLAY_RATE, set_key=True)
out.append("Called set_key=True at display frame 5")

# Count after
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            for ch in t.get_sections()[0].get_all_channels():
                if 'pressU' in ch.get_name() and 'CTRL_L' in ch.get_name():
                    after = ch.get_num_keys()
                    out.append(f"pressU keys after: {after}")
                    if after > before:
                        out.append("KEY CREATED!")
                    else:
                        out.append("No new key created")
                    break
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
