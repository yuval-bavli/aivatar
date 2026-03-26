"""Get face skeleton bone names, especially jaw/mouth bones."""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    face_mesh = unreal.load_asset("/Game/MetaHumans/model4/Face/SKM_model4_FaceMesh")
    skel = face_mesh.get_editor_property('skeleton')
    p(f"Skeleton: {skel.get_name()}")

    # Get bone names from the skeletal mesh
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    face_comp = None
    for actor in actors:
        if 'bp_model4' in actor.get_name().lower():
            for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
                if comp.get_name() == "Face":
                    face_comp = comp
                    break
            break

    if face_comp:
        bone_names = face_comp.get_all_bone_names()
        p(f"\nTotal bones: {len(bone_names)}")

        # Show all jaw/mouth/tongue bones
        p("\n=== Jaw/Mouth/Tongue bones ===")
        for b in bone_names:
            name = str(b)
            if any(k in name.lower() for k in ['jaw', 'mouth', 'lip', 'tongue', 'chin', 'teeth']):
                # Get bone transform
                try:
                    xf = face_comp.get_bone_transform_by_name(b, unreal.SpaceType.COMPONENT_SPACE)
                    loc = xf.translation
                    rot = xf.rotation.rotator()
                    p(f"  {name}: pos=({loc.x:.2f},{loc.y:.2f},{loc.z:.2f}) rot=({rot.pitch:.1f},{rot.yaw:.1f},{rot.roll:.1f})")
                except:
                    p(f"  {name}")

        # Show ALL bones (first 50)
        p(f"\n=== All bones (first 60) ===")
        for b in bone_names[:60]:
            p(f"  {b}")
        if len(bone_names) > 60:
            p(f"  ... and {len(bone_names)-60} more")

except Exception as e:
    p(f"ERROR: {e}")
    import traceback
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
