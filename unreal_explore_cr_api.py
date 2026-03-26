"""Explore ControlRigSequencerLibrary and related APIs."""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

# 1. ControlRigSequencerLibrary methods
p("=== ControlRigSequencerLibrary ===")
lib = unreal.ControlRigSequencerLibrary
for attr in sorted(dir(lib)):
    if not attr.startswith('_'):
        p(f"  {attr}")

# 2. ControlRigBlueprintLibrary methods
p("\n=== ControlRigBlueprintLibrary ===")
lib2 = unreal.ControlRigBlueprintLibrary
for attr in sorted(dir(lib2)):
    if not attr.startswith('_'):
        p(f"  {attr}")

# 3. MovieSceneControlRigParameterSection methods
p("\n=== MovieSceneControlRigParameterSection ===")
sec_cls = unreal.MovieSceneControlRigParameterSection
for attr in sorted(dir(sec_cls)):
    if not attr.startswith('_') and callable(getattr(sec_cls, attr, None)):
        p(f"  {attr}()")

# 4. ControlRigPoseAsset
p("\n=== ControlRigPoseAsset ===")
pose_cls = unreal.ControlRigPoseAsset
for attr in sorted(dir(pose_cls)):
    if not attr.startswith('_') and callable(getattr(pose_cls, attr, None)):
        p(f"  {attr}()")

# 5. Check ControlRig class itself
p("\n=== ControlRig ===")
cr_cls = unreal.ControlRig
for attr in sorted(dir(cr_cls)):
    if not attr.startswith('_') and callable(getattr(cr_cls, attr, None)):
        # Filter to interesting methods
        low = attr.lower()
        if any(k in low for k in ['control', 'value', 'set', 'get', 'key', 'pose']):
            p(f"  {attr}()")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
