"""
After load_anim_sequence bound all 219 channels properly,
set jaw values directly on bound channels and verify.
"""
import unreal, io, traceback, re

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

TICKS = 800

try:
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

    face_track = None
    for binding in level_seq.get_bindings():
        for track in binding.get_tracks():
            if "Face_ControlBoard" in str(track.get_display_name()):
                face_track = track
                break
        if face_track: break

    sec = face_track.get_sections()[0]
    channels = sec.get_all_channels()
    p(f"Total channels: {len(channels)}")

    # Build channel map
    ch_map = {}
    for ch in channels:
        name = ch.get_name()
        # Strip numeric suffix (e.g., _17)
        base = re.sub(r'_\d+$', '', name)
        ch_map[base] = ch

    # List jaw channels
    p("\n=== Jaw channels ===")
    for key in sorted(ch_map.keys()):
        if 'jaw' in key.lower():
            ch = ch_map[key]
            keys = ch.get_keys()
            vals = [round(k.get_value(), 4) for k in keys]
            p(f"  {key} -> {ch.get_name()}: vals={vals}")

    # List lip channels
    p("\n=== Lip channels ===")
    for key in sorted(ch_map.keys()):
        if 'lip' in key.lower():
            ch = ch_map[key]
            keys = ch.get_keys()
            vals = [round(k.get_value(), 4) for k in keys[:3]]
            p(f"  {key} -> {ch.get_name()}: vals={vals}")

    # Now modify jaw channels to extreme values
    p("\n=== Keying jaw channels ===")

    # Clear all existing keys first
    for ch in channels:
        for k in reversed(ch.get_keys()):
            ch.remove_key(k)
    p("Cleared all keys")

    # Key at frame 0 (rest), frame 30 (jaw open), frame 60 (rest)
    fn0 = unreal.FrameNumber(0)
    fn30 = unreal.FrameNumber(30 * TICKS)
    fn60 = unreal.FrameNumber(60 * TICKS)

    # Set all channels to 0 at frame 0 and 60
    for ch in channels:
        ch.add_key(fn0, 0.0)
        ch.add_key(fn60, 0.0)

    # Set jaw channels at frame 30
    jaw_channels_to_key = {
        "CTRL_C_jaw.X": 0.0,
        "CTRL_C_jaw.Y": -1.0,  # Full jaw down
        "CTRL_C_jaw_openExtreme": 1.0,  # Full extreme open
    }

    for ctrl_name, value in jaw_channels_to_key.items():
        if ctrl_name in ch_map:
            ch = ch_map[ctrl_name]
            ch.add_key(fn30, value)
            p(f"  Keyed {ctrl_name} = {value} at frame 30 (channel: {ch.get_name()})")
        else:
            p(f"  NOT FOUND: {ctrl_name}")

    # Verify keys
    p("\n=== Verify jaw keys ===")
    for key in sorted(ch_map.keys()):
        if 'jaw' in key.lower() and ('openExtreme' in key or key.endswith('.Y') or key.endswith('.X')):
            ch = ch_map[key]
            keys = ch.get_keys()
            for k in keys:
                frame = k.get_time().frame_number.value // TICKS
                p(f"  {key}: frame={frame} val={k.get_value():.4f}")

    # Set section range
    sec.set_start_frame_bounded(True)
    sec.set_start_frame(0)
    sec.set_end_frame_bounded(True)
    sec.set_end_frame(90 * TICKS)

    # Scrub to frame 30
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30 * TICKS)
    p("\nScrubbed to frame 30")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE - CHECK VIEWPORT ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
