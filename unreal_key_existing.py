"""
Key directly on the existing rig channels using channel.add_key().
First, list the initial channels to find the right ones.
Then remove the phantom channels created by add_scalar_parameter_key.
"""
import unreal, io, re

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
face_section = None
face_track = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            face_track = track
            face_section = track.get_sections()[0]
            break
    if face_section: break

channels = face_section.get_all_channels()
p(f"Total channels: {len(channels)}")

# Remove phantom parameters (the ones created by add_vector2d_parameter_key)
try:
    face_section.remove_vector2d_parameter("CTRL_C_jaw")
    p("Removed phantom CTRL_C_jaw parameter")
except: pass

channels = face_section.get_all_channels()
p(f"Channels after cleanup: {len(channels)}")

# Build map of channels by name
ch_by_name = {}
for ch in channels:
    ch_by_name[ch.get_name()] = ch

# List jaw/mouth channels with their names
p("\n=== Initial rig channels (jaw/mouth) ===")
jaw_mouth = [(n, ch) for n, ch in ch_by_name.items()
             if 'jaw' in n.lower() or 'mouth' in n.lower() or 'tongue' in n.lower()]
for n, ch in sorted(jaw_mouth):
    p(f"  {n} ({type(ch).__name__})")

# Find the CTRL_C_jaw.Y channel (should be suffix _0 on a fresh section)
jaw_y = None
for n, ch in ch_by_name.items():
    if re.match(r'CTRL_C_jaw\.Y_\d+$', n):
        jaw_y = ch
        p(f"\nFound jaw.Y channel: {n}")
        break

if jaw_y:
    # Try add_key with just (FrameNumber, value)
    TICKS = 800

    # Key at frame 0 (rest) and frame 100 (aa = wide open)
    try:
        # The add_key signature for MovieSceneScriptingFloatChannel:
        # add_key(time, new_value, sub_frame=0.0, time_unit=DISPLAY_RATE)
        # or add_key(time, new_value)

        fn0 = unreal.FrameNumber(0)
        fn100 = unreal.FrameNumber(100 * TICKS)

        jaw_y.add_key(fn0, 0.0)
        p(f"add_key(frame 0, 0.0) -> OK")

        jaw_y.add_key(fn100, -0.9)
        p(f"add_key(frame 100, -0.9) -> OK")

        # Read back
        keys = jaw_y.get_keys()
        p(f"\nKeys: {len(keys)}")
        for k in keys:
            p(f"  tick={k.get_time().frame_number.value}, val={k.get_value()}")
    except Exception as e:
        p(f"add_key error: {e}")
        import traceback
        p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
