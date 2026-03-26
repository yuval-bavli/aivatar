"""Get face skeleton bone names using correct API."""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    face_mesh = unreal.load_asset("/Game/MetaHumans/model4/Face/SKM_model4_FaceMesh")
    skel = face_mesh.get_editor_property('skeleton')

    # Get bone names from skeleton
    # Try different methods
    for attr in dir(skel):
        if 'bone' in attr.lower() and ('name' in attr.lower() or 'get' in attr.lower()):
            if not attr.startswith('_') and callable(getattr(skel, attr, None)):
                p(f"skel.{attr}")

    # Use SkeletalMesh to get bone info
    mesh_data = face_mesh
    for attr in dir(mesh_data):
        if 'bone' in attr.lower() and ('name' in attr.lower() or 'get' in attr.lower() or 'num' in attr.lower()):
            if not attr.startswith('_'):
                p(f"mesh.{attr}")

    # Try AnimationLibrary
    anim_lib = unreal.AnimationLibrary
    for attr in dir(anim_lib):
        if 'bone' in attr.lower():
            p(f"AnimLib.{attr}")

    # Try getting bone count and names from the mesh
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
        num_bones = face_comp.get_num_bones()
        p(f"\nTotal bones: {num_bones}")
        p("\n=== Jaw/Mouth/Tongue bones ===")
        for i in range(num_bones):
            name = face_comp.get_bone_name(i)
            name_str = str(name)
            if any(k in name_str.lower() for k in ['jaw', 'mouth', 'lip', 'tongue', 'chin', 'teeth']):
                p(f"  [{i}] {name_str}")

        p(f"\n=== First 50 bones ===")
        for i in range(min(50, num_bones)):
            p(f"  [{i}] {face_comp.get_bone_name(i)}")

except Exception as e:
    p(f"ERROR: {e}")
    import traceback
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
