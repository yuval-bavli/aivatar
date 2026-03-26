"""Re-add the Face_ControlBoard_CtrlRig track to the Face binding."""
import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
world = unreal.EditorLevelLibrary.get_editor_world()

# Find face binding
face_binding = None
for b in level_seq.get_bindings():
    if b.get_display_name() == "Face":
        face_binding = b
        break

out.append(f"Face binding: {face_binding.get_display_name() if face_binding else 'NOT FOUND'}")

# Find the Face_ControlBoard_CtrlRig class/asset
# The control rig should be on the face skeletal mesh component
face_rig_class = unreal.load_class(None, "/Script/ControlRig.ControlRig")
out.append(f"ControlRig class: {face_rig_class}")

# Try using the library to add/bind the control rig
# Check available methods
try:
    # Try load_anim_blueprint_by_path_to_control_rig or similar
    # Actually, let's try finding the control rig asset
    face_cr_asset = unreal.load_object(None, "/Game/MetaHumans/model4/Face/Face_ControlBoard_CtrlRig")
    out.append(f"Face CR asset: {face_cr_asset}")
except:
    out.append("Could not load face CR asset directly")

# Try to find it via the actor's components
actors = unreal.EditorLevelLibrary.get_all_level_actors()
for actor in actors:
    if "model4" in actor.get_name():
        out.append(f"Actor: {actor.get_name()}")
        comps = actor.get_components_by_class(unreal.SkeletalMeshComponent)
        for comp in comps:
            out.append(f"  Component: {comp.get_name()}")
            # Check for anim blueprint / control rig
            anim_inst = comp.get_anim_instance()
            if anim_inst:
                out.append(f"    Anim instance: {anim_inst.get_class().get_name()}")

# Try to use lib.set_control_rig_track_filter or similar to re-add
# Actually try creating a new track on the binding
try:
    # The add_track method needs a track type
    new_track = face_binding.add_track(unreal.MovieSceneControlRigParameterTrack)
    out.append(f"Added new track: {new_track}")
except Exception as e:
    out.append(f"add_track failed: {e}")

# List all tracks now
for t in face_binding.get_tracks():
    out.append(f"Track: {t.get_display_name()}")
    for s in t.get_sections():
        channels = s.get_all_channels()
        out.append(f"  Section channels: {len(channels)}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
