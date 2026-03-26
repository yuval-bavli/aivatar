"""
Fix jaw by modifying channel key values directly, then force re-evaluation.
Also test if scrubbing makes the rig pick up the new values.
"""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
lib = unreal.ControlRigSequencerLibrary

rigs = lib.get_control_rigs(level_seq)
face_rig = None
for proxy in rigs:
    cr = proxy.control_rig
    if "Face" in cr.get_name():
        face_rig = cr
        break

TICKS = 800
TR = unreal.MovieSceneTimeUnit.TICK_RESOLUTION

# Step 1: Clear all jaw keys
face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            break

jaw_y_ch = None
jaw_x_ch = None
for ch in face_section.get_all_channels():
    name = ch.get_name()
    if 'jaw.Y' in name and 'open' not in name.lower():
        jaw_y_ch = ch
    if 'jaw.X' in name and 'open' not in name.lower():
        jaw_x_ch = ch

# Clear jaw Y and X
for ch in [jaw_y_ch, jaw_x_ch]:
    if ch:
        for k in reversed(list(ch.get_keys())):
            ch.remove_key(k)
        out.append(f"Cleared {ch.get_name()}")

# Step 2: Key jaw at frame 50 with extreme value using vec2d API
frame = 50
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)
lib.set_local_control_rig_vector2d(level_seq, face_rig, "CTRL_C_jaw",
    unreal.FrameNumber(frame * TICKS), unreal.Vector2D(0, -1.0),
    time_unit=TR, set_key=True)

# Check the key
keys = list(jaw_y_ch.get_keys())
out.append(f"After vec2d key: {len(keys)} keys, val={keys[0].get_value():.4f}" if keys else "No keys!")

# Step 3: Now modify the key value
if keys:
    keys[0].set_value(-1.0)
    out.append(f"Set key value to -1.0, readback: {keys[0].get_value():.4f}")

# Step 4: Scrub away and back to force evaluation
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)
out.append(f"Scrubbed to frame {frame}")

# Step 5: Also try approach B - use add_key on the channel directly
# Add a key at frame 100 with value -0.8
from unreal import FrameNumber as FN
frame2 = 100
try:
    # Use channel.add_key to create a key with the correct value
    new_key = jaw_y_ch.add_key(
        unreal.FrameNumber(frame2),  # display rate frame
        -0.8,
        0.0  # sub-frame
    )
    out.append(f"\nadd_key at frame {frame2}: success")
    # Read back
    keys2 = list(jaw_y_ch.get_keys())
    out.append(f"jaw.Y now has {len(keys2)} keys:")
    for k in keys2:
        out.append(f"  frame={k.get_time().frame_number.value} val={k.get_value():.4f}")
except Exception as e:
    out.append(f"add_key failed: {e}")

# Screenshot
unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, "test.png")
out.append("\nScreenshot taken")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
