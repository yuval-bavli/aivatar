"""
Clean test: fresh section, then ONLY use set_control_value + send_auto_key_event.
Check if keys land on the ORIGINAL channels (not phantoms).
"""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

TICKS = 800

try:
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
    seq_lib = unreal.LevelSequenceEditorBlueprintLibrary

    # Get face track
    face_track = None
    for binding in level_seq.get_bindings():
        for track in binding.get_tracks():
            if "Face_ControlBoard" in str(track.get_display_name()):
                face_track = track
                break
        if face_track: break

    # Remove all sections, add fresh one
    for sec in face_track.get_sections():
        face_track.remove_section(sec)
    new_sec = face_track.add_section()
    new_sec.set_start_frame_bounded(False)
    new_sec.set_end_frame_bounded(False)

    channels_before = new_sec.get_all_channels()
    p(f"Fresh section: {len(channels_before)} channels")

    # Record all channel names
    names_before = set()
    for ch in channels_before:
        names_before.add(ch.get_name())

    # Show jaw channels
    p("\nJaw channels BEFORE:")
    for ch in channels_before:
        name = ch.get_name()
        if 'jaw' in name.lower() and ('openExtreme' in name or name.startswith('CTRL_C_jaw.')):
            p(f"  {name}")

    # Get CR
    proxies = lib.get_control_rigs(level_seq)
    cr = None
    for proxy in proxies:
        if 'Face_ControlBoard' in proxy.control_rig.get_name():
            cr = proxy.control_rig
            break
    hierarchy = cr.get_hierarchy()

    # Enable interaction
    lib.set_interaction(True)

    # Go to frame 50
    seq_lib.set_current_time(50 * TICKS)

    # Set jaw_openExtreme via hierarchy and auto-key
    oe_key = unreal.RigElementKey()
    oe_key.name = "CTRL_C_jaw_openExtreme"
    oe_key.type = unreal.RigElementType.CONTROL

    hierarchy.set_control_value(oe_key, hierarchy.make_control_value_from_float(0.8),
                                value_type=unreal.RigControlValueType.CURRENT)
    hierarchy.send_auto_key_event(oe_key)
    p("\nSet jaw_openExtreme=0.8 at frame 50, sent auto-key event")

    # Also try jaw.Y as float directly (not Vector2D)
    # The channel is CTRL_C_jaw.Y - maybe we can find and key it as a sub-control?
    jaw_key = unreal.RigElementKey()
    jaw_key.name = "CTRL_C_jaw"
    jaw_key.type = unreal.RigElementType.CONTROL
    hierarchy.set_control_value(jaw_key,
        hierarchy.make_control_value_from_vector2d(unreal.Vector2D(0, -0.9)),
        value_type=unreal.RigControlValueType.CURRENT)
    hierarchy.send_auto_key_event(jaw_key)
    p("Set jaw=(0,-0.9) at frame 50, sent auto-key event")

    lib.set_interaction(False)

    # Check channels AFTER
    channels_after = new_sec.get_all_channels()
    names_after = set()
    for ch in channels_after:
        names_after.add(ch.get_name())

    new_channels = names_after - names_before
    p(f"\nChannels after: {len(channels_after)}")
    p(f"NEW channels created: {len(new_channels)}")
    for n in sorted(new_channels):
        p(f"  NEW: {n}")

    # Check ALL keyed channels
    p("\nKeyed channels:")
    for ch in channels_after:
        keys = ch.get_keys()
        if len(keys) > 0:
            name = ch.get_name()
            is_new = "NEW" if name in new_channels else "ORIGINAL"
            vals = []
            for k in keys:
                vals.append((k.get_time().frame_number.value // TICKS, k.get_value()))
            p(f"  [{is_new}] {name}: {vals}")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
