"""
Try: Close sequencer, then set control values to see if the rig works at all.
Also try: remove all sections so sequencer doesn't override.
"""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

    # First, remove all sections from face track to stop sequencer overriding
    face_track = None
    for binding in level_seq.get_bindings():
        for track in binding.get_tracks():
            if "Face_ControlBoard" in str(track.get_display_name()):
                face_track = track
                break
        if face_track: break

    for sec in face_track.get_sections():
        face_track.remove_section(sec)
    p("Removed all Face sections (sequencer won't override)")

    # Now get the rig and set values
    proxies = lib.get_control_rigs(level_seq)
    cr = None
    for proxy in proxies:
        if 'Face_ControlBoard' in proxy.control_rig.get_name():
            cr = proxy.control_rig
            break

    hierarchy = cr.get_hierarchy()

    # Set jaw wide open
    jaw_key = unreal.RigElementKey()
    jaw_key.name = "CTRL_C_jaw"
    jaw_key.type = unreal.RigElementType.CONTROL
    new_val = hierarchy.make_control_value_from_vector2d(unreal.Vector2D(0, -0.9))
    hierarchy.set_control_value(jaw_key, new_val, value_type=unreal.RigControlValueType.CURRENT)
    p("Set jaw to (0, -0.9)")

    # Also try INITIAL value type
    hierarchy.set_control_value(jaw_key, new_val, value_type=unreal.RigControlValueType.INITIAL)
    p("Set jaw INITIAL to (0, -0.9)")

    # Read back
    cur = hierarchy.get_control_value(jaw_key, value_type=unreal.RigControlValueType.CURRENT)
    v2d = hierarchy.get_vector2d_from_control_value(cur)
    p(f"Readback: x={v2d.x}, y={v2d.y}")

    # Set jaw_openExtreme
    oe_key = unreal.RigElementKey()
    oe_key.name = "CTRL_C_jaw_openExtreme"
    oe_key.type = unreal.RigElementType.CONTROL
    hierarchy.set_control_value(oe_key, hierarchy.make_control_value_from_float(0.9),
                                value_type=unreal.RigControlValueType.CURRENT)
    hierarchy.set_control_value(oe_key, hierarchy.make_control_value_from_float(0.9),
                                value_type=unreal.RigControlValueType.INITIAL)
    p("Set jaw_openExtreme to 0.9")

    # Set mouth controls for maximum visibility
    for side in ["CTRL_L_", "CTRL_R_"]:
        for ctrl_name in ["mouth_lowerLipDepress", "mouth_upperLipRaise", "mouth_stretch"]:
            key = unreal.RigElementKey()
            key.name = side + ctrl_name
            key.type = unreal.RigElementType.CONTROL
            val = hierarchy.make_control_value_from_float(0.9)
            hierarchy.set_control_value(key, val, value_type=unreal.RigControlValueType.CURRENT)
            hierarchy.set_control_value(key, val, value_type=unreal.RigControlValueType.INITIAL)
    p("Set mouth controls to 0.9")

    p("\nCHECK VIEWPORT - face should have wide open mouth!")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
