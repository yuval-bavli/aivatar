"""
New approach: 
1. Load the 1-frame rest anim into the section (which properly binds channels)
2. Then key directly on the properly-bound channels
"""
import unreal, io, traceback

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
    p(f"Channels: {len(channels)}")

    # Build channel map by base name (strip _N suffix)
    import re
    ch_map = {}
    for ch in channels:
        name = ch.get_name()
        base = re.sub(r'_\d+$', '', name)
        ch_map[base] = ch

    p(f"Channel bases: {len(ch_map)}")

    # Check jaw channels
    for key in sorted(ch_map.keys()):
        if 'jaw' in key.lower() and ('openExtreme' in key or key.endswith('.Y') or key.endswith('.X')):
            ch = ch_map[key]
            keys = ch.get_keys()
            p(f"  {key}: {len(keys)} keys, channel={ch.get_name()}")
            for k in keys:
                p(f"    tick={k.get_time().frame_number.value} val={k.get_value()}")

    # Now try keying on these properly-bound channels
    # First clear all existing keys
    for ch in channels:
        keys = ch.get_keys()
        for k in reversed(keys):
            ch.remove_key(k)

    p("\nCleared all keys")

    # Key jaw_openExtreme at frames 0, 50, 100
    oe_ch = ch_map.get("CTRL_C_jaw_openExtreme")
    if oe_ch:
        oe_ch.add_key(unreal.FrameNumber(0), 0.0)
        oe_ch.add_key(unreal.FrameNumber(50 * TICKS), 0.8)
        oe_ch.add_key(unreal.FrameNumber(100 * TICKS), 0.0)
        keys = oe_ch.get_keys()
        p(f"\njaw_openExtreme: {len(keys)} keys on channel {oe_ch.get_name()}")
        for k in keys:
            p(f"  tick={k.get_time().frame_number.value} val={k.get_value()}")

    # Key jaw.Y
    jaw_y = ch_map.get("CTRL_C_jaw.Y")
    if jaw_y:
        jaw_y.add_key(unreal.FrameNumber(0), 0.0)
        jaw_y.add_key(unreal.FrameNumber(50 * TICKS), -0.7)
        jaw_y.add_key(unreal.FrameNumber(100 * TICKS), 0.0)
        keys = jaw_y.get_keys()
        p(f"\njaw.Y: {len(keys)} keys on channel {jaw_y.get_name()}")
        for k in keys:
            p(f"  tick={k.get_time().frame_number.value} val={k.get_value()}")

    # Set section range
    sec.set_start_frame_bounded(True)
    sec.set_start_frame(0)
    sec.set_end_frame_bounded(True)
    sec.set_end_frame(150 * TICKS)

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE - SCRUB TO FRAME 50 ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
