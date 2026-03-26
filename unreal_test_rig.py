"""
Test: directly manipulate the Control Rig to see if the face responds.
Also try the channel.add_key() approach instead of section.add_scalar_parameter_key().
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

# Find the face mesh / skeletal mesh component
actors = unreal.EditorLevelLibrary.get_all_level_actors()
p("=== All actors ===")
for a in actors:
    label = a.get_actor_label()
    cls = type(a).__name__
    p(f"  {label} ({cls})")
    if "model4" in label.lower() or "metahuman" in label.lower() or "bp_model4" in label.lower():
        p(f"    *** Potential character ***")
        # List components
        comps = a.get_components_by_class(unreal.ActorComponent)
        for c in comps:
            cname = c.get_name()
            ctype = type(c).__name__
            p(f"    Component: {cname} ({ctype})")

# Try to find and manipulate control rig instance
p("\n=== Looking for ControlRig instances ===")
for a in actors:
    comps = a.get_components_by_class(unreal.SkeletalMeshComponent)
    for smc in comps:
        p(f"\nSkeletalMeshComponent: {smc.get_name()} on {a.get_actor_label()}")
        # Check for anim instance
        try:
            anim = smc.get_anim_instance()
            if anim:
                p(f"  AnimInstance: {type(anim).__name__}")
                # Check for control rig methods
                cr_methods = [m for m in dir(anim) if 'control' in m.lower() or 'rig' in m.lower()]
                p(f"  Control/Rig methods: {cr_methods}")
        except Exception as e:
            p(f"  AnimInstance: {e}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
