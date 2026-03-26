"""
Test: Set a Control Rig control value directly, then see if we can key it.
Approach: Find the ControlRig instance, set control values, use sequencer to key.
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

# 1. Find the Face_ControlBoard_CtrlRig in the level
# Look through all actors for the BP_model4 with a face skeletal mesh
actors = unreal.EditorLevelLibrary.get_all_level_actors()
p(f"Total actors: {len(actors)}")

for actor in actors:
    name = actor.get_name()
    cls = type(actor).__name__
    if 'model4' in name.lower() or 'bp_model' in name.lower():
        p(f"\nFound: {name} ({cls})")
        # List components
        components = actor.get_components_by_class(unreal.ActorComponent)
        for comp in components:
            comp_name = comp.get_name()
            comp_cls = type(comp).__name__
            if 'face' in comp_name.lower() or 'control' in comp_name.lower() or 'skeletal' in comp_cls.lower():
                p(f"  Component: {comp_name} ({comp_cls})")

# 2. Try to find ControlRig components
p("\n=== Looking for ControlRig components ===")
for actor in actors:
    components = actor.get_components_by_class(unreal.ActorComponent)
    for comp in components:
        comp_cls = type(comp).__name__
        if 'controlrig' in comp_cls.lower() or 'control_rig' in comp_cls.lower():
            p(f"  {actor.get_name()} -> {comp.get_name()} ({comp_cls})")

# 3. Check what classes are available for Control Rig
p("\n=== Available ControlRig classes ===")
for attr in dir(unreal):
    if 'controlrig' in attr.lower() or 'control_rig' in attr.lower():
        p(f"  unreal.{attr}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
