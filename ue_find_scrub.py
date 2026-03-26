"""
Figure out the correct way to scrub the sequencer to specific frames.
Test different approaches and verify which one actually moves the playhead.
"""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
lslib = unreal.LevelSequenceEditorBlueprintLibrary

# Check sequencer info
out.append("=== Sequencer Info ===")
try:
    cur_time = lslib.get_current_time()
    out.append(f"Current time: {cur_time}")
except Exception as e:
    out.append(f"get_current_time: {e}")

try:
    fps = level_seq.get_display_rate()
    out.append(f"Display rate: {fps}")
except Exception as e:
    out.append(f"Display rate: {e}")

try:
    pr = level_seq.get_playback_range()
    out.append(f"Playback range: {pr}")
except Exception as e:
    out.append(f"Playback range: {e}")

try:
    tr = level_seq.get_tick_resolution()
    out.append(f"Tick resolution: {tr}")
except Exception as e:
    out.append(f"Tick resolution: {e}")

# List all methods on LevelSequenceEditorBlueprintLibrary
methods = [m for m in dir(lslib) if 'time' in m.lower() or 'frame' in m.lower() or 'scrub' in m.lower() or 'position' in m.lower()]
out.append(f"\nTime/frame methods: {methods}")

# Try set_current_time with different values and read back
out.append("\n=== Testing set_current_time ===")
test_values = [0, 10, 800, 8000, 10*800, 30*800]
for val in test_values:
    lslib.set_current_time(val)
    cur = lslib.get_current_time()
    out.append(f"  set_current_time({val}) -> get_current_time() = {cur}")

# Try set_current_time in frames (maybe it takes frames not ticks?)
out.append("\n=== Testing with small values (frames?) ===")
for val in [0, 10, 30, 100]:
    lslib.set_current_time(val)
    cur = lslib.get_current_time()
    out.append(f"  set({val}) -> get() = {cur}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
