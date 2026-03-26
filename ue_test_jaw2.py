"""Test jaw keying and verify tick positions."""
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

# Clear jaw.Y channel first
face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            break

if face_section:
    for ch in face_section.get_all_channels():
        if 'jaw.Y' in ch.get_name() and 'open' not in ch.get_name().lower():
            keys = list(ch.get_keys())
            for k in reversed(keys):
                ch.remove_key(k)
            out.append(f"Cleared jaw.Y: {len(keys)} keys removed")
            break

# Scrub to frame 50 and key jaw at -1.0
frame = 50
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)

lib.set_local_control_rig_vector2d(level_seq, face_rig, "CTRL_C_jaw",
    unreal.FrameNumber(frame * TICKS), unreal.Vector2D(0, -1.0),
    time_unit=TR, set_key=True)
out.append(f"Keyed jaw at frame {frame}")

# Read back
if face_section:
    for ch in face_section.get_all_channels():
        if 'jaw.Y' in ch.get_name() and 'open' not in ch.get_name().lower():
            keys = list(ch.get_keys())
            out.append(f"jaw.Y: {len(keys)} keys")
            for k in keys:
                out.append(f"  tick={k.get_time().frame_number.value} val={k.get_value():.4f}")
            break
        if 'jaw.X' in ch.get_name():
            keys = list(ch.get_keys())
            out.append(f"jaw.X: {len(keys)} keys")
            for k in keys:
                out.append(f"  tick={k.get_time().frame_number.value} val={k.get_value():.4f}")

# Now also try keying with DISPLAY_RATE to compare
frame2 = 80
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame2 * TICKS)

DR = unreal.MovieSceneTimeUnit.DISPLAY_RATE
lib.set_local_control_rig_vector2d(level_seq, face_rig, "CTRL_C_jaw",
    unreal.FrameNumber(frame2), unreal.Vector2D(0, -0.5),
    time_unit=DR, set_key=True)
out.append(f"\nKeyed jaw at frame {frame2} with DISPLAY_RATE")

# Read back again
if face_section:
    for ch in face_section.get_all_channels():
        if 'jaw.Y' in ch.get_name() and 'open' not in ch.get_name().lower():
            keys = list(ch.get_keys())
            out.append(f"jaw.Y: {len(keys)} keys now")
            for k in keys:
                out.append(f"  tick={k.get_time().frame_number.value} val={k.get_value():.4f}")
            break

# Screenshot
unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, "test.png")
out.append("\nScreenshot taken at frame 80")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
