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

    # List jaw controls
    controls = hierarchy.get_controls()
    jaw_controls = [c for c in controls if 'jaw' in c.name.lower()]
    p(f"Jaw controls: {len(jaw_controls)}")
    for c in jaw_controls:
        p(f"  {c.name}")

    # Try to set jaw value
    jaw_key = unreal.RigElementKey()
    jaw_key.name = "CTRL_C_jaw"
    jaw_key.type = unreal.RigElementType.CONTROL

    # Read current
    try:
        cur = hierarchy.get_control_value(jaw_key, value_type=unreal.RigControlValueType.CURRENT)
        p(f"Current jaw: {cur}")
        v2d = hierarchy.get_vector2d_from_control_value(cur)
        p(f"  as v2d: x={v2d.x}, y={v2d.y}")
    except Exception as e:
        p(f"Read error: {e}")

    # Set jaw open
    try:
        new_val = hierarchy.make_control_value_from_vector2d(unreal.Vector2D(0, -0.9))
        hierarchy.set_control_value(jaw_key, new_val, value_type=unreal.RigControlValueType.CURRENT)
        p("Set jaw to (0, -0.9) OK!")
    except Exception as e:
        p(f"Set error: {e}")
        p(traceback.format_exc())

    # Read back
    try:
        cur2 = hierarchy.get_control_value(jaw_key, value_type=unreal.RigControlValueType.CURRENT)
        v2d2 = hierarchy.get_vector2d_from_control_value(cur2)
        p(f"After set: x={v2d2.x}, y={v2d2.y}")
    except Exception as e:
        p(f"Read back error: {e}")

    # Also try jaw_openExtreme
    try:
        oe_key = unreal.RigElementKey()
        oe_key.name = "CTRL_C_jaw_openExtreme"
        oe_key.type = unreal.RigElementType.CONTROL
        new_val2 = hierarchy.make_control_value_from_float(0.8)
        hierarchy.set_control_value(oe_key, new_val2, value_type=unreal.RigControlValueType.CURRENT)
        p("Set jaw_openExtreme to 0.8 OK!")
    except Exception as e:
        p(f"jaw_openExtreme error: {e}")

except Exception as e:
    p(f"TOP LEVEL ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE - CHECK VIEWPORT ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
