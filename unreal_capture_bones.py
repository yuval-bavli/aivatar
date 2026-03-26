"""
Test: set jaw controls, evaluate rig, check if bone transforms change.
"""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    # Find face mesh component
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    face_mesh_comp = None
    for actor in actors:
        if 'bp_model4' in actor.get_name().lower():
            for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
                if comp.get_name() == "Face":
                    face_mesh_comp = comp
                    break
            break

    check_bones = ["FACIAL_C_Jaw", "FACIAL_C_Chin", "FACIAL_C_TeethLower",
                    "FACIAL_C_LipLower", "FACIAL_C_LipUpper", "FACIAL_C_Tongue1"]

    # Read rest transforms
    p("=== REST POSE ===")
    rest = {}
    for bn in check_bones:
        t = face_mesh_comp.get_socket_transform(bn)
        rest[bn] = (t.translation.x, t.translation.y, t.translation.z,
                     t.rotation.rotator().pitch, t.rotation.rotator().yaw, t.rotation.rotator().roll)
        p(f"  {bn}: loc=({t.translation.x:.2f},{t.translation.y:.2f},{t.translation.z:.2f})")

    # Get control rig
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
    proxies = lib.get_control_rigs(level_seq)
    cr = None
    for proxy in proxies:
        if 'Face_ControlBoard' in proxy.control_rig.get_name():
            cr = proxy.control_rig
            break

    hierarchy = cr.get_hierarchy()
    controls = hierarchy.get_controls()

    # Build control key lookup
    ctrl_by_name = {}
    for c in controls:
        ctrl_by_name[str(c.name)] = c

    # Set jaw open
    p("\n=== Setting jaw controls ===")
    jaw_key = ctrl_by_name.get("CTRL_C_jaw")
    if jaw_key:
        val = hierarchy.make_control_value_from_vector2d(unreal.Vector2D(0, -0.8))
        hierarchy.set_control_value(jaw_key, val)
        p(f"  Set CTRL_C_jaw = (0, -0.8)")

    oe_key = ctrl_by_name.get("CTRL_C_jaw_openExtreme")
    if oe_key:
        val = hierarchy.make_control_value_from_float(0.9)
        hierarchy.set_control_value(oe_key, val)
        p(f"  Set CTRL_C_jaw_openExtreme = 0.9")

    # Try to evaluate
    try:
        cr.evaluate()
        p("  cr.evaluate() OK")
    except Exception as e:
        p(f"  evaluate error: {e}")

    # Read again
    p("\n=== AFTER JAW OPEN ===")
    for bn in check_bones:
        t = face_mesh_comp.get_socket_transform(bn)
        r = rest[bn]
        dx = t.translation.x - r[0]
        dy = t.translation.y - r[1]
        dz = t.translation.z - r[2]
        moved = abs(dx) + abs(dy) + abs(dz) > 0.01
        tag = " <<< MOVED" if moved else ""
        p(f"  {bn}: loc=({t.translation.x:.2f},{t.translation.y:.2f},{t.translation.z:.2f}) delta=({dx:.3f},{dy:.3f},{dz:.3f}){tag}")

    # Also check get_ref_pose_transform and get_delta_transform_from_ref_pose
    p("\n=== get_delta_transform_from_ref_pose ===")
    for bn in check_bones:
        try:
            delta = face_mesh_comp.get_delta_transform_from_ref_pose(bn)
            loc = delta.translation
            rot = delta.rotation.rotator()
            has_delta = abs(loc.x) + abs(loc.y) + abs(loc.z) + abs(rot.pitch) + abs(rot.yaw) + abs(rot.roll) > 0.001
            tag = " <<< HAS DELTA" if has_delta else ""
            p(f"  {bn}: dloc=({loc.x:.3f},{loc.y:.3f},{loc.z:.3f}) drot=({rot.pitch:.3f},{rot.yaw:.3f},{rot.roll:.3f}){tag}")
        except Exception as e:
            p(f"  {bn}: error {e}")

    # Reset
    if jaw_key:
        val = hierarchy.make_control_value_from_vector2d(unreal.Vector2D(0, 0))
        hierarchy.set_control_value(jaw_key, val)
    if oe_key:
        val = hierarchy.make_control_value_from_float(0.0)
        hierarchy.set_control_value(oe_key, val)
    p("\nReset controls")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
