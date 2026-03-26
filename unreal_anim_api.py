"""Check AnimationLibrary and AnimSequence APIs for adding bone animation data."""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

# Check AnimationLibrary methods
AnimLib = unreal.AnimationLibrary
p("=== AnimationLibrary methods ===")
for m in sorted(dir(AnimLib)):
    if not m.startswith('_'):
        p(f"  {m}")

p("\n=== AnimSequence methods (add/set related) ===")
anim_seq = unreal.load_asset("/Game/Aivatar/VisemePoses")
if anim_seq:
    for m in sorted(dir(anim_seq)):
        if not m.startswith('_') and any(k in m.lower() for k in ['add', 'set', 'bone', 'track', 'curve', 'key', 'raw']):
            p(f"  {m}")

# Check if AnimationBlueprintLibrary exists
p("\n=== AnimationBlueprintLibrary ===")
try:
    ABLib = unreal.AnimationBlueprintLibrary
    for m in sorted(dir(ABLib)):
        if not m.startswith('_') and any(k in m.lower() for k in ['add', 'bone', 'track', 'curve', 'key', 'transform']):
            p(f"  {m}")
except:
    p("  Not available")

# Check AnimSequenceFactory
p("\n=== Factories ===")
try:
    factory = unreal.AnimSequenceFactory()
    for m in sorted(dir(factory)):
        if not m.startswith('_') and any(k in m.lower() for k in ['skeleton', 'target', 'bone']):
            p(f"  {m}")
except Exception as e:
    p(f"  AnimSequenceFactory error: {e}")

# Check if we can get bone ref pose data from skeleton
p("\n=== Skeleton ref pose ===")
skel = unreal.load_asset("/Game/MetaHumans/Common/Face/Face_Archetype_Skeleton")
if skel:
    p(f"Skeleton: {skel.get_name()}")
    skel_methods = [m for m in dir(skel) if not m.startswith('_') and any(k in m.lower() for k in ['bone', 'ref', 'pose', 'transform'])]
    for m in sorted(skel_methods):
        p(f"  {m}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
