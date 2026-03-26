"""
Properly set up a Face_ControlBoard_CtrlRig track on the Face binding.
Explore ControlRigSequencerLibrary methods for binding control rigs.
"""
import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# List all methods on ControlRigSequencerLibrary
methods = [m for m in dir(lib) if not m.startswith('_')]
out.append("ControlRigSequencerLibrary methods:")
for m in methods:
    out.append(f"  {m}")

# Find face binding
face_binding = None
for b in level_seq.get_bindings():
    if b.get_display_name() == "Face":
        face_binding = b
        break

out.append(f"\nFace binding: {face_binding.get_display_name()}")

# Try find_or_create_control_rig_component_and_link or similar
# Try to load the control rig blueprint
cr_class = None
try:
    cr_class = unreal.load_class(None, "/Game/MetaHumans/model4/Face/Face_ControlBoard_CtrlRig.Face_ControlBoard_CtrlRig_C")
    out.append(f"CR class via _C: {cr_class}")
except:
    try:
        cr_class = unreal.load_class(None, "/Game/MetaHumans/model4/Face/Face_ControlBoard_CtrlRig")
        out.append(f"CR class: {cr_class}")
    except:
        out.append("Could not load CR class")

# Try to find the CR blueprint asset
try:
    cr_bp = unreal.load_asset("/Game/MetaHumans/model4/Face/Face_ControlBoard_CtrlRig")
    out.append(f"CR blueprint: {cr_bp} type={type(cr_bp).__name__}")
except:
    out.append("Could not load CR blueprint")

# Search for the CR in common MetaHuman paths
search_paths = [
    "/Game/MetaHumans/Common/Face/Face_ControlBoard_CtrlRig",
    "/Game/MetaHumans/model4/Face/Face_ControlBoard_CtrlRig",
    "/Engine/Plugins/MetaHuman/Content/Face_ControlBoard_CtrlRig",
]
for p in search_paths:
    try:
        asset = unreal.load_asset(p)
        if asset:
            out.append(f"Found at {p}: {type(asset).__name__}")
    except:
        pass

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
