"""Direct approach: set control values on the rig hierarchy."""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

    proxies = lib.get_control_rigs(level_seq)
    cr = None
    for proxy in proxies:
        if 'Face_ControlBoard' in proxy.control_rig.get_name():
            cr = proxy.control_rig
            break

    p(f"CR: {cr.get_name()}")
    hierarchy = cr.get_hierarchy()

    # Set jaw value directly
    jaw_key = unreal.RigElementKey()
    jaw_key.name = "CTRL_C_jaw"
    jaw_key.type = unreal.RigElementType.CONTROL

    # Read current
    cur = hierarchy.get_control_value(jaw_key, value_type=unreal.RigControlValueType.CURRENT)
    v2d = hierarchy.get_vector2d_from_control_value(cur)
    p(f"Current jaw: x={v2d.x}, y={v2d.y}")

    # Set jaw wide open
    new_val = hierarchy.make_control_value_from_vector2d(unreal.Vector2D(0, -0.9))
    hierarchy.set_control_value(jaw_key, new_val, value_type=unreal.RigControlValueType.CURRENT)
    p("Set jaw to (0, -0.9)")

    # Read back
    cur2 = hierarchy.get_control_value(jaw_key, value_type=unreal.RigControlValueType.CURRENT)
    v2d2 = hierarchy.get_vector2d_from_control_value(cur2)
    p(f"After set: x={v2d2.x}, y={v2d2.y}")

    # Set jaw_openExtreme
    oe_key = unreal.RigElementKey()
    oe_key.name = "CTRL_C_jaw_openExtreme"
    oe_key.type = unreal.RigElementType.CONTROL
    new_val2 = hierarchy.make_control_value_from_float(0.8)
    hierarchy.set_control_value(oe_key, new_val2, value_type=unreal.RigControlValueType.CURRENT)
    p("Set jaw_openExtreme to 0.8")

    # Set some mouth controls
    for side in ["CTRL_L_", "CTRL_R_"]:
        for ctrl_name in ["mouth_lowerLipDepress", "mouth_upperLipRaise", "mouth_stretch"]:
            key = unreal.RigElementKey()
            key.name = side + ctrl_name
            key.type = unreal.RigElementType.CONTROL
            val = hierarchy.make_control_value_from_float(0.6)
            hierarchy.set_control_value(key, val, value_type=unreal.RigControlValueType.CURRENT)
    p("Set mouth controls to 0.6")

    p("\nAll values set - CHECK VIEWPORT FOR OPEN MOUTH!")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
