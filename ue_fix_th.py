import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

if not level_seq:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: No level sequence open")
    raise SystemExit

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

# Scrub to frame
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)

# 1. jaw_openExtreme - Clear old value
lib.set_local_control_rig_float(level_seq, face_rig, "CTRL_C_jaw_openExtreme", 
    unreal.FrameNumber(frame * TICKS), 0.0, time_unit=TR, set_key=True)
# 2. tongue_inOut - Set user value
lib.set_local_control_rig_float(level_seq, face_rig, "CTRL_C_tongue_inOut", 
    unreal.FrameNumber(frame * TICKS), -0.2, time_unit=TR, set_key=True)
# 3. CTRL_C_jaw (vector2D) - Set user value Y=0.15
lib.set_local_control_rig_vector2d(level_seq, face_rig, "CTRL_C_jaw",
    unreal.FrameNumber(frame * TICKS), unreal.Vector2D(0, 0.15), time_unit=TR, set_key=True)
# 4. CTRL_C_tongue_tipMove (vector2D) - Clear old value
lib.set_local_control_rig_vector2d(level_seq, face_rig, "CTRL_C_tongue_tipMove",
    unreal.FrameNumber(frame * TICKS), unreal.Vector2D(0, 0.0), time_unit=TR, set_key=True)

# Important: Patch Vector2D values on channels
face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            break

patched_channels = []
for ch in face_section.get_all_channels():
    full_name = ch.get_name()
    if "CTRL_C_jaw.X" in full_name:
        for k in ch.get_keys():
            if k.get_time().frame_number.value == frame:
                k.set_value(0.0)
                patched_channels.append(full_name)
    elif "CTRL_C_jaw.Y" in full_name:
        for k in ch.get_keys():
            if k.get_time().frame_number.value == frame:
                k.set_value(0.15)
                patched_channels.append(full_name)
    elif "CTRL_C_tongue_tipMove.X" in full_name:
        for k in ch.get_keys():
            if k.get_time().frame_number.value == frame:
                k.set_value(0.0)
                patched_channels.append(full_name)
    elif "CTRL_C_tongue_tipMove.Y" in full_name:
        for k in ch.get_keys():
            if k.get_time().frame_number.value == frame:
                k.set_value(0.0)
                patched_channels.append(full_name)

out.append(f"Fixed TH frame with user values! Patched channels: {patched_channels}")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
