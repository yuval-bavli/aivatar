"""Get reference pose bone transforms and test adding keys to AnimSequence."""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    AnimLib = unreal.AnimationLibrary
    skel = unreal.load_asset("/Game/MetaHumans/Common/Face/Face_Archetype_Skeleton")
    ref_pose = skel.get_reference_pose()

    # Get jaw/mouth bone ref transforms
    jaw_bones = ["FACIAL_C_Jaw", "FACIAL_C_TeethLower", "FACIAL_C_LipLower",
                  "FACIAL_C_LipUpper", "FACIAL_C_Tongue1", "FACIAL_C_MouthLower",
                  "FACIAL_C_MouthUpper", "FACIAL_C_Chin"]

    p("=== Ref pose (bone-local transforms) ===")
    for bn in jaw_bones:
        try:
            t = ref_pose.get_ref_pose_relative_transform(unreal.Name(bn))
            loc = t.translation
            rot = t.rotation.rotator()
            p(f"  {bn}: loc=({loc.x:.4f},{loc.y:.4f},{loc.z:.4f}) rot=({rot.pitch:.4f},{rot.yaw:.4f},{rot.roll:.4f})")
        except Exception as e:
            p(f"  {bn}: error {e}")

    # Now test adding transform keys to an AnimSequence
    p("\n=== Test add_transformation_curve_key ===")

    # First check if we need to create a fresh anim or can reuse
    anim_seq = unreal.load_asset("/Game/Aivatar/VisemePoses")
    p(f"Anim: {anim_seq.get_name()}, frames={AnimLib.get_num_frames(anim_seq)}")

    # Try to remove all existing bone animation
    try:
        AnimLib.remove_all_bone_animation(anim_seq)
        p("Removed all bone animation")
    except Exception as e:
        p(f"remove_all_bone_animation error: {e}")

    # Try add_transformation_curve_key with various args
    test_transform = unreal.Transform()
    test_transform.translation = unreal.Vector(0, 0, 0)
    test_transform.rotation = unreal.Quat(0, 0, 0, 1)
    test_transform.scale3d = unreal.Vector(1, 1, 1)

    # Try: (anim_seq, bone_name, time, transform)
    try:
        AnimLib.add_transformation_curve_key(anim_seq, "FACIAL_C_Jaw", 0.0, test_transform)
        p("add_transformation_curve_key(seq, name, time, transform) OK!")
    except Exception as e:
        p(f"Attempt 1: {e}")

    # Try with Name type
    try:
        AnimLib.add_transformation_curve_key(anim_seq, unreal.Name("FACIAL_C_Jaw"), 0.0, test_transform)
        p("Attempt 2 (Name) OK!")
    except Exception as e:
        p(f"Attempt 2: {e}")

    # Try with different arg order
    try:
        AnimLib.add_transformation_curve_key(
            animation_sequence_base=anim_seq,
            curve_name="FACIAL_C_Jaw",
            time=0.0,
            transform=test_transform
        )
        p("Attempt 3 (kwargs) OK!")
    except Exception as e:
        p(f"Attempt 3: {e}")

    # Try finalize
    try:
        AnimLib.finalize_bone_animation(anim_seq)
        p("finalize OK!")
    except Exception as e:
        p(f"finalize error: {e}")

    p(f"\nFrames after: {AnimLib.get_num_frames(anim_seq)}")
    p(f"Tracks after: {len(AnimLib.get_animation_track_names(anim_seq))}")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
