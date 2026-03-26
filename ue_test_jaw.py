"""
Test: manually set jaw wide open at current frame, then take screenshot.
This verifies whether channel key modification actually affects the rig.
"""
import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# Get face rig
rigs = lib.get_control_rigs(level_seq)
face_rig = None
for proxy in rigs:
    cr = proxy.control_rig
    if "Face" in cr.get_name():
        face_rig = cr
        break

TICKS = 800
TR = unreal.MovieSceneTimeUnit.TICK_RESOLUTION

# Scrub to frame 30
frame = 30
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)
out.append(f"Scrubbed to frame {frame}")

# Now try setting jaw via the float API on the Y component directly
# The vec2d API might be broken - let's see if there's a way to set jaw.Y as a float
# First check what current jaw value is via the rig
try:
    val = face_rig.get_control_value(unreal.RigElementKey(
        name="CTRL_C_jaw", type=unreal.RigElementType.CONTROL))
    out.append(f"Current jaw value: {val}")
except Exception as e:
    out.append(f"get_control_value error: {e}")

# Try setting the jaw value directly on the control rig
try:
    face_rig.set_control_value(
        unreal.RigElementKey(name="CTRL_C_jaw", type=unreal.RigElementType.CONTROL),
        unreal.Vector2D(0, -1.0))
    out.append("Set jaw to (0, -1.0) via set_control_value")
except Exception as e:
    out.append(f"set_control_value error: {e}")

# Also check what the section channels look like in detail
face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            break

if face_section:
    for ch in face_section.get_all_channels():
        name = ch.get_name()
        if 'jaw.Y' in name and 'open' not in name.lower():
            keys = list(ch.get_keys())
            out.append(f"\n{name}: {len(keys)} keys")
            # Check the section's range
            out.append(f"Section range: {face_section.get_range()}")
            # Check channel default value
            try:
                out.append(f"Channel default: {ch.get_default()}")
            except:
                pass
            for k in keys:
                t = k.get_time()
                fn = t.frame_number
                out.append(f"  FrameNumber={fn.value} value={k.get_value():.4f}")
            break

# Now key with set_local_control_rig_vector2d and check if it creates at the right tick
try:
    lib.set_local_control_rig_vector2d(level_seq, face_rig, "CTRL_C_jaw",
        unreal.FrameNumber(frame * TICKS), unreal.Vector2D(0, -1.0),
        time_unit=TR, set_key=True)
    out.append(f"\nKeyed jaw at frame {frame} with (-1.0)")
except Exception as e:
    out.append(f"Key error: {e}")

# Read back again
if face_section:
    for ch in face_section.get_all_channels():
        name = ch.get_name()
        if 'jaw.Y' in name and 'open' not in name.lower():
            keys = list(ch.get_keys())
            out.append(f"\nAfter keying - {name}: {len(keys)} keys")
            for k in keys:
                out.append(f"  FrameNumber={k.get_time().frame_number.value} value={k.get_value():.4f}")
            break

# Take screenshot
try:
    unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, "test.png")
    out.append("\nScreenshot taken")
except Exception as e:
    out.append(f"Screenshot error: {e}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
