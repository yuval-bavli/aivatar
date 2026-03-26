"""
Create viseme AnimSequence with bone transformation curves.
Step 1: Create a fresh AnimSequence, set proper length, add jaw bone transforms.
"""
import unreal, io, traceback, math

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

TICKS = 800
FPS = 30.0

try:
    AnimLib = unreal.AnimationLibrary
    skel = unreal.load_asset("/Game/MetaHumans/Common/Face/Face_Archetype_Skeleton")
    ref_pose = skel.get_reference_pose()

    # Ref pose for jaw bone
    jaw_ref = ref_pose.get_bone_pose(unreal.Name("FACIAL_C_Jaw"))
    p(f"Jaw ref: loc=({jaw_ref.translation.x:.4f},{jaw_ref.translation.y:.4f},{jaw_ref.translation.z:.4f}) " +
      f"rot=({jaw_ref.rotation.rotator().pitch:.4f},{jaw_ref.rotation.rotator().yaw:.4f},{jaw_ref.rotation.rotator().roll:.4f})")

    # Delete and recreate the AnimSequence to start completely fresh
    anim_path = "/Game/Aivatar/VisemePoses"

    # Create fresh anim
    p("\n=== Creating fresh AnimSequence ===")

    # Use AssetToolsHelpers
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.AnimSequenceFactory()
    factory.set_editor_property('target_skeleton', skel)

    # Delete old one first
    old = unreal.load_asset(anim_path)
    if old:
        unreal.EditorAssetLibrary.delete_asset(anim_path)
        p("Deleted old VisemePoses")

    anim_seq = asset_tools.create_asset("VisemePoses", "/Game/Aivatar", unreal.AnimSequence, factory)
    p(f"Created: {anim_seq.get_name()}")

    # Check settable properties
    p(f"Initial frames: {AnimLib.get_num_frames(anim_seq)}")
    p(f"Initial length: {AnimLib.get_sequence_length(anim_seq):.3f}s")

    # Try to set number of frames or length
    try:
        anim_seq.set_editor_property('number_of_frames', 150)
        p("Set number_of_frames = 150")
    except Exception as e:
        p(f"set number_of_frames error: {e}")

    try:
        anim_seq.set_editor_property('sequence_length', 5.0)
        p("Set sequence_length = 5.0")
    except Exception as e:
        p(f"set sequence_length error: {e}")

    # Try set_rate_scale
    try:
        AnimLib.set_rate_scale(anim_seq, 1.0)
        p("Set rate_scale = 1.0")
    except Exception as e:
        p(f"set_rate_scale error: {e}")

    p(f"After settings: frames={AnimLib.get_num_frames(anim_seq)}, length={AnimLib.get_sequence_length(anim_seq):.3f}s")

    # Now add bone transform keys
    # Rest transform (identity - additive on top of ref pose)
    rest = unreal.Transform()
    rest.translation = unreal.Vector(0, 0, 0)
    rest.rotation = unreal.Quat(0, 0, 0, 1)
    rest.scale3d = unreal.Vector(1, 1, 1)

    # Jaw open - the jaw ref pose has roll=40, so we need to add more rotation
    # The jaw bone's roll axis is what opens/closes the mouth
    # Adding negative roll should open the jaw (rotate it away from upper jaw)
    angles_to_try = [10, 20, 30]
    for deg in [20]:  # Try 20 degrees
        rad = math.radians(deg / 2.0)
        jaw_open = unreal.Transform()
        jaw_open.translation = unreal.Vector(0, 0, 0)
        # Rotate around the local Z axis (roll in UE) to open jaw more
        # Actually, let's try around pitch (Y in UE local space)
        # First try: roll rotation (around Forward/X axis)
        jaw_open.rotation = unreal.Quat(0, 0, math.sin(rad), math.cos(rad))
        jaw_open.scale3d = unreal.Vector(1, 1, 1)

    # Add keys at different times
    # frame 0 = rest, frame 50 = jaw open, frame 100 = rest
    times = [0.0, 50.0/FPS, 100.0/FPS]  # 0, 1.667, 3.333 seconds
    transforms = [rest, jaw_open, rest]

    p("\n=== Adding bone keys ===")
    for t, tr in zip(times, transforms):
        AnimLib.add_transformation_curve_key(anim_seq, "FACIAL_C_Jaw", t, tr)
        p(f"  FACIAL_C_Jaw at t={t:.3f}s")

    # Also add for teeth lower (attached to jaw)
    for t, tr in zip(times, transforms):
        AnimLib.add_transformation_curve_key(anim_seq, "FACIAL_C_TeethLower", t, tr)

    # Finalize
    AnimLib.finalize_bone_animation(anim_seq)
    p(f"\nAfter finalize: frames={AnimLib.get_num_frames(anim_seq)}, length={AnimLib.get_sequence_length(anim_seq):.3f}s")

    # Check what the anim contains
    tracks = AnimLib.get_animation_track_names(anim_seq)
    p(f"Bone tracks: {len(tracks)}")
    for tn in tracks:
        p(f"  {tn}")

    # Check raw data
    try:
        data = AnimLib.get_raw_track_data(anim_seq, "FACIAL_C_Jaw")
        p(f"Raw track data for jaw: {data}")
    except Exception as e:
        p(f"get_raw_track_data error: {e}")

    # Try to get transformation keys back
    try:
        keys = AnimLib.get_transformation_keys(anim_seq, "FACIAL_C_Jaw")
        p(f"Transformation keys: {len(keys)}")
        for k in keys[:5]:
            p(f"  {k}")
    except Exception as e:
        p(f"get_transformation_keys error: {e}")

    # Now try loading into CR section
    p("\n=== Loading into CR section ===")
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

    face_track = None
    for binding in level_seq.get_bindings():
        for track in binding.get_tracks():
            if "Face_ControlBoard" in str(track.get_display_name()):
                face_track = track
                break
        if face_track: break

    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    face_mesh_comp = None
    for actor in actors:
        if 'bp_model4' in actor.get_name().lower():
            for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
                if comp.get_name() == "Face":
                    face_mesh_comp = comp
                    break
            break

    sec = face_track.get_sections()[0]

    try:
        lib.load_anim_sequence_into_control_rig_section(
            sec, anim_seq, face_mesh_comp, unreal.FrameNumber(0))
        p("load OK!")
    except Exception as e:
        p(f"load error: {e}")

    # Check keyed channels
    keyed = 0
    nonzero_keyed = 0
    for ch in sec.get_all_channels():
        keys = ch.get_keys()
        if len(keys) > 0:
            keyed += 1
            has_nonzero = any(abs(k.get_value()) > 0.001 for k in keys)
            if has_nonzero:
                nonzero_keyed += 1
                name = ch.get_name()
                if nonzero_keyed <= 10:
                    vals = [(round(k.get_time().frame_number.value/TICKS), round(k.get_value(),4)) for k in keys[:5]]
                    p(f"  {name}: {vals}")
    p(f"\nKeyed: {keyed}, with nonzero values: {nonzero_keyed}")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
