"""
Test: key Control Rig channels directly instead of using add_scalar_parameter_key.
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

# Find the ORIGINAL _0 channels for jaw.Y
p("=== Looking for _0 channels (original rig channels) ===")
jaw_y_channels = []
for ch in channels:
    name = ch.get_name()
    if "CTRL_C_jaw.Y" in name:
        try: nk = ch.get_num_keys()
        except: nk = "?"
        jaw_y_channels.append((name, ch, nk))
        p(f"  {name} [{nk} keys]")

# Try keying directly on a _0 channel
target_ch = None
for name, ch, nk in jaw_y_channels:
    if name.endswith("_0"):
        target_ch = ch
        break

if target_ch:
    p(f"\nTarget channel: {target_ch.get_name()}")
    p(f"Channel type: {type(target_ch).__name__}")

    # List available methods on the channel
    methods = [m for m in dir(target_ch) if not m.startswith('_') and ('key' in m.lower() or 'add' in m.lower() or 'set' in m.lower())]
    p(f"Key-related methods: {methods}")

    # Try adding a key directly
    TICKS_PER_FRAME = 800
    frame100_tick = 100 * TICKS_PER_FRAME
    fn = unreal.FrameNumber(frame100_tick)

    try:
        target_ch.add_key(fn, -0.9, 0.0, unreal.SequenceTimeUnit.TICK_RESOLUTION)
        p(f"add_key at frame 100 with value -0.9 -> OK")
    except Exception as e:
        p(f"add_key error: {e}")

    try:
        target_ch.add_key(unreal.FrameNumber(frame100_tick), -0.9)
        p(f"add_key(fn, -0.9) -> OK")
    except Exception as e:
        p(f"add_key(fn, val) error: {e}")

    # Check what methods are available
    all_methods = [m for m in dir(target_ch) if not m.startswith('_')]
    p(f"\nAll methods: {all_methods}")

    # Read keys back
    try:
        keys = target_ch.get_keys()
        p(f"\nKeys after attempt: {len(keys)}")
        for k in keys:
            p(f"  frame={k.get_time().frame_number.value}, val={k.get_value()}")
    except Exception as e:
        p(f"get_keys error: {e}")
else:
    p("No _0 channel found for CTRL_C_jaw.Y")
    # Maybe the _0 channels were cleared? Let's check what suffix exists
    p("\nAll jaw channels:")
    for ch in channels:
        n = ch.get_name()
        if "jaw" in n.lower():
            p(f"  {n}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
