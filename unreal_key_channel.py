"""
Key visemes by directly adding keys to existing channels using channel.add_key().
This bypasses add_scalar_parameter_key which creates new parameter entries.
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
face_section = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            sections = track.get_sections()
            if sections:
                face_section = sections[0]
                break
    if face_section: break

channels = face_section.get_all_channels()

# Build a channel lookup by base name (strip _N suffix)
import re
ch_map = {}
for ch in channels:
    name = ch.get_name()
    base = re.sub(r'_\d+$', '', name)
    ch_map[base] = ch

p(f"Total channels: {len(channels)}")
p(f"Unique base names: {len(ch_map)}")

# Test: find CTRL_C_jaw.Y channel and use channel.add_key()
test_ch = ch_map.get("CTRL_C_jaw.Y")
if test_ch:
    p(f"\nTarget: {test_ch.get_name()} ({type(test_ch).__name__})")

    # List all methods
    methods = [m for m in dir(test_ch) if not m.startswith('_')]
    p(f"Methods: {methods}")

    # First clear existing keys
    try:
        keys = test_ch.get_keys()
        p(f"Current keys: {len(keys)}")
        for k in reversed(list(keys)):
            test_ch.remove_key(k)
        p(f"Cleared all keys")
    except Exception as e:
        p(f"Clear error: {e}")

    # Now try add_key with different signatures
    TICKS = 800

    # Frame 0: val=0 (rest)
    try:
        fn0 = unreal.FrameNumber(0)
        test_ch.add_key(fn0, 0.0, 0.0, unreal.SequenceTimeUnit.TICK_RESOLUTION)
        p("add_key(fn, val, interp, TICK_RESOLUTION) -> OK")
    except Exception as e:
        p(f"add_key attempt 1: {e}")

    try:
        test_ch.add_key(unreal.FrameNumber(0), 0.0)
        p("add_key(fn, val) -> OK")
    except Exception as e:
        p(f"add_key attempt 2: {e}")

    # Frame 100: val=-0.7 (aa wide open)
    try:
        fn100 = unreal.FrameNumber(100 * TICKS)
        test_ch.add_key(fn100, -0.7, 0.0, unreal.SequenceTimeUnit.TICK_RESOLUTION)
        p("add_key at frame 100 -> OK")
    except Exception as e:
        p(f"add_key frame 100 attempt 1: {e}")

    try:
        test_ch.add_key(unreal.FrameNumber(100 * TICKS), -0.7)
        p("add_key(fn100, -0.7) -> OK")
    except Exception as e:
        p(f"add_key frame 100 attempt 2: {e}")

    # Try set_default
    try:
        test_ch.set_default(0.0)
        p("set_default(0.0) -> OK")
    except Exception as e:
        p(f"set_default: {e}")

    # Read back
    try:
        keys = test_ch.get_keys()
        p(f"\nAfter keying: {len(keys)} keys")
        for k in keys:
            p(f"  frame={k.get_time().frame_number.value}, val={k.get_value()}")
    except Exception as e:
        p(f"Readback error: {e}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
