"""Test the freshly recreated track - check section and try keying."""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

    # Find face track
    face_track = None
    for binding in level_seq.get_bindings():
        for track in binding.get_tracks():
            if "Face_ControlBoard" in str(track.get_display_name()):
                face_track = track
                break
        if face_track: break

    sections = face_track.get_sections()
    p(f"Sections: {len(sections)}")

    if len(sections) == 0:
        # Add a section
        sec = face_track.add_section()
        sec.set_start_frame_bounded(False)
        sec.set_end_frame_bounded(False)
        p("Added new section")
    else:
        sec = sections[0]

    channels = sec.get_all_channels()
    p(f"Channels: {len(channels)}")

    # Show first few channel names to check suffix
    p("\nFirst 10 channels:")
    for ch in channels[:10]:
        p(f"  {ch.get_name()}")

    # Check jaw channels specifically
    p("\nJaw channels:")
    for ch in channels:
        name = ch.get_name()
        if 'jaw' in name.lower():
            p(f"  {name}")

    # Now try keying through the proper API
    TICKS = 800
    proxies = lib.get_control_rigs(level_seq)
    cr = None
    for proxy in proxies:
        if 'Face_ControlBoard' in proxy.control_rig.get_name():
            cr = proxy.control_rig
            break
    p(f"\nCR: {cr.get_name()}")

    # Key jaw open at frame 50
    fn0 = unreal.FrameNumber(0)
    fn50 = unreal.FrameNumber(50 * TICKS)
    fn100 = unreal.FrameNumber(100 * TICKS)

    # Use set_local_control_rig_float for scalar controls
    lib.set_local_control_rig_float(level_seq, cr, "CTRL_C_jaw_openExtreme", fn50, 0.8)
    p("Keyed jaw_openExtreme=0.8 at frame 50")

    # Use set_local_control_rig_vector2d for jaw
    lib.set_local_control_rig_vector2d(level_seq, cr, "CTRL_C_jaw", fn50, unreal.Vector2D(0, -0.7))
    p("Keyed jaw=(0,-0.7) at frame 50")

    # Rest at frame 0 and 100
    lib.set_local_control_rig_vector2d(level_seq, cr, "CTRL_C_jaw", fn0, unreal.Vector2D(0, 0))
    lib.set_local_control_rig_float(level_seq, cr, "CTRL_C_jaw_openExtreme", fn0, 0.0)
    lib.set_local_control_rig_vector2d(level_seq, cr, "CTRL_C_jaw", fn100, unreal.Vector2D(0, 0))
    lib.set_local_control_rig_float(level_seq, cr, "CTRL_C_jaw_openExtreme", fn100, 0.0)
    p("Keyed rest at frames 0 and 100")

    # Check channels again
    channels = sec.get_all_channels()
    p(f"\nChannels after keying: {len(channels)}")
    for ch in channels:
        try:
            keys = ch.get_keys()
            if len(keys) > 0:
                name = ch.get_name()
                vals = [(k.get_time().frame_number.value // TICKS, k.get_value()) for k in keys]
                p(f"  {name}: {vals}")
        except:
            pass

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE - SCRUB TO FRAME 50 AND CHECK FACE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
