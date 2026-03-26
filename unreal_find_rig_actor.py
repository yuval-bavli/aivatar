"""Find ControlRig through the actor's skeletal mesh, not through sequencer."""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    # Find BP_model4 actor
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    bp_actor = None
    for a in actors:
        if 'bp_model4' in a.get_name().lower():
            bp_actor = a
            break

    if not bp_actor:
        p("BP_model4 not found!")
    else:
        p(f"Actor: {bp_actor.get_name()}")

        # List ALL components
        all_comps = bp_actor.get_components_by_class(unreal.ActorComponent)
        p(f"Total components: {len(all_comps)}")
        for comp in all_comps:
            p(f"  {comp.get_name()} ({type(comp).__name__})")

        # Try to find ControlRigComponent
        try:
            cr_comps = bp_actor.get_components_by_class(unreal.ControlRigComponent)
            p(f"\nControlRigComponents: {len(cr_comps)}")
            for crc in cr_comps:
                p(f"  {crc.get_name()}")
        except Exception as e:
            p(f"ControlRigComponent search error: {e}")

        # Find Face skeletal mesh and check for anim instance
        face_mesh = None
        for comp in all_comps:
            if comp.get_name() == "Face" and isinstance(comp, unreal.SkeletalMeshComponent):
                face_mesh = comp
                break

        if face_mesh:
            p(f"\nFace mesh: {face_mesh.get_name()}")
            p(f"  Anim class: {face_mesh.get_editor_property('anim_class')}")

            anim_inst = face_mesh.get_anim_instance()
            if anim_inst:
                p(f"  Anim instance: {type(anim_inst).__name__}")
                for attr in dir(anim_inst):
                    if 'control' in attr.lower() or 'rig' in attr.lower():
                        p(f"    anim.{attr}")
            else:
                p("  No anim instance")

    # Also try ControlRig.find_control_rigs
    p("\n=== ControlRig.find_control_rigs ===")
    try:
        found = unreal.ControlRig.find_control_rigs()
        p(f"Found: {len(found)}")
        for r in found:
            p(f"  {r.get_name()} ({type(r).__name__})")
    except Exception as e:
        p(f"Error: {e}")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
