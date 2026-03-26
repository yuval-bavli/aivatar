"""
Export the viseme animation from the FaceExport level sequence as FBX.
Uses SequencerTools.export_level_sequence_fbx for automated export.
"""
import unreal

out = []

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
if not level_seq:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: No level sequence open")
    raise SystemExit

out.append(f"Sequence: {level_seq.get_name()}")

world = unreal.EditorLevelLibrary.get_editor_world()
out.append(f"World: {world.get_name()}")

# Get bindings - we need the Face binding
bindings = level_seq.get_bindings()
face_binding = None
for b in bindings:
    bname = b.get_display_name()
    out.append(f"Binding: {bname}")
    if "Face" == bname:
        face_binding = b
    # Also collect tracks for this binding
    for track in b.get_tracks():
        out.append(f"  Track: {track.get_display_name()}")

if not face_binding:
    out.append("WARNING: No 'Face' binding found, will export all bindings")

# Get tracks from Face binding
face_tracks = []
if face_binding:
    face_tracks = list(face_binding.get_tracks())

# Setup export params
params = unreal.SequencerExportFBXParams()
params.world = world
params.sequence = level_seq
params.root_sequence = level_seq
params.fbx_file_name = "c:/Users/yuval/src/aivatar/viseme_animation.fbx"

# Include all bindings (Face, Body, BP_model4)
params.bindings = list(bindings)

# Include face tracks
if face_tracks:
    params.tracks = face_tracks

# Override options
opts = unreal.FbxExportOption()
opts.ascii = False
opts.export_morph_targets = True
opts.export_local_time = True
opts.fbx_export_compatibility = unreal.FbxExportCompatibility.FBX_2018
opts.bake_actor_animation = unreal.MovieSceneBakeType.BAKE_TRANSFORMS
opts.level_of_detail = True
params.override_options = opts

out.append(f"\nExporting to: {params.fbx_file_name}")
out.append(f"Bindings: {len(params.bindings)}")
out.append(f"Tracks: {len(params.tracks)}")

try:
    result = unreal.SequencerTools.export_level_sequence_fbx(params)
    out.append(f"Export result: {result}")
except Exception as e:
    out.append(f"Export error: {e}")

# Also try exporting to AnimSequence first (alternative approach)
# This bakes control rig -> bone animation
out.append("\n--- Alternative: Bake to AnimSequence ---")
try:
    # Create an AnimSequence asset
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # First check if the anim sequence already exists
    anim_seq = unreal.load_asset("/Game/Aivatar/VisemeAnimation")
    if not anim_seq:
        # Create a new AnimSequence
        factory = unreal.AnimSequenceFactory()
        # We need the skeleton - get it from the face mesh
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        face_skel = None
        for actor in actors:
            if "model4" in actor.get_name():
                comps = actor.get_components_by_class(unreal.SkeletalMeshComponent)
                for comp in comps:
                    if comp.get_name() == "Face":
                        mesh = comp.get_skeletal_mesh_asset()
                        if mesh:
                            face_skel = mesh.get_editor_property("skeleton")
                            out.append(f"Face skeleton: {face_skel.get_name() if face_skel else 'None'}")
                        break

        if face_skel:
            factory.set_editor_property("target_skeleton", face_skel)
            anim_seq = asset_tools.create_asset("VisemeAnimation", "/Game/Aivatar", unreal.AnimSequence, factory)
            out.append(f"Created AnimSequence: {anim_seq.get_name() if anim_seq else 'Failed'}")
    else:
        out.append(f"Found existing AnimSequence: {anim_seq.get_name()}")

    if anim_seq and face_binding:
        export_opts = unreal.AnimSeqExportOption()
        result2 = unreal.SequencerTools.export_anim_sequence(
            world, level_seq, anim_seq, export_opts, face_binding, True)
        out.append(f"AnimSequence export result: {result2}")
except Exception as e:
    out.append(f"AnimSequence error: {e}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
