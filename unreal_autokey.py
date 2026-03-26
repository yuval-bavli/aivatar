"""
Use the auto-key system to key control rig values - mimicking UI behavior.
1. Enable auto-key in sequencer
2. Set interaction mode
3. Set control value
4. Trigger auto-key event
"""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

TICKS = 800

try:
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
    seq_lib = unreal.LevelSequenceEditorBlueprintLibrary

    # Check auto-key state
    p("=== Sequencer state ===")
    for attr in dir(seq_lib):
        if 'auto' in attr.lower() or 'key' in attr.lower():
            p(f"  seq_lib.{attr}")

    # Enable auto-key
    try:
        seq_lib.set_auto_key_enabled(True)
        p(f"Auto-key enabled: {seq_lib.is_auto_key_enabled()}")
    except Exception as e:
        p(f"Auto-key error: {e}")

    # Get Face CR
    proxies = lib.get_control_rigs(level_seq)
    cr = None
    for proxy in proxies:
        if 'Face_ControlBoard' in proxy.control_rig.get_name():
            cr = proxy.control_rig
            break

    hierarchy = cr.get_hierarchy()

    # Enable interaction
    lib.set_interaction(True)
    p("Interaction enabled")

    # Go to frame 50
    seq_lib.set_current_time(50 * TICKS)
    p("At frame 50")

    # Set jaw value via hierarchy
    jaw_key = unreal.RigElementKey()
    jaw_key.name = "CTRL_C_jaw"
    jaw_key.type = unreal.RigElementType.CONTROL

    new_val = hierarchy.make_control_value_from_vector2d(unreal.Vector2D(0, -0.9))
    hierarchy.set_control_value(jaw_key, new_val, value_type=unreal.RigControlValueType.CURRENT)
    p("Set jaw to (0, -0.9)")

    # Try send_auto_key_event
    try:
        hierarchy.send_auto_key_event(jaw_key)
        p("send_auto_key_event(jaw) OK!")
    except Exception as e:
        p(f"send_auto_key_event error: {e}")

    # Also try jaw_openExtreme
    oe_key = unreal.RigElementKey()
    oe_key.name = "CTRL_C_jaw_openExtreme"
    oe_key.type = unreal.RigElementType.CONTROL
    hierarchy.set_control_value(oe_key, hierarchy.make_control_value_from_float(0.8),
                                value_type=unreal.RigControlValueType.CURRENT)
    try:
        hierarchy.send_auto_key_event(oe_key)
        p("send_auto_key_event(jaw_openExtreme) OK!")
    except Exception as e:
        p(f"send_auto_key_event error: {e}")

    # Check what got keyed
    face_track = None
    for binding in level_seq.get_bindings():
        for track in binding.get_tracks():
            if "Face_ControlBoard" in str(track.get_display_name()):
                face_track = track
                break
        if face_track: break

    sec = face_track.get_sections()[0]
    p(f"\nKeyed channels:")
    for ch in sec.get_all_channels():
        keys = ch.get_keys()
        if len(keys) > 0:
            name = ch.get_name()
            vals = [(k.get_time().frame_number.value // TICKS, k.get_value()) for k in keys]
            p(f"  {name}: {vals}")

    lib.set_interaction(False)

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
