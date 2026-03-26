"""Re-add Face_ControlBoard_CtrlRig track using find_or_create_control_rig_track."""
import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# Load the control rig blueprint
cr_bp = unreal.load_asset("/Game/MetaHumans/Common/Face/Face_ControlBoard_CtrlRig")
out.append(f"CR Blueprint: {cr_bp.get_name() if cr_bp else 'None'}")

# Get the class from the blueprint
cr_class = cr_bp.generated_class() if hasattr(cr_bp, 'generated_class') else None
if not cr_class:
    try:
        cr_class = cr_bp.get_editor_property("generated_class")
    except:
        pass
out.append(f"CR Class: {cr_class}")

# Find face binding
face_binding = None
for b in level_seq.get_bindings():
    if b.get_display_name() == "Face":
        face_binding = b
        break

# Try find_or_create_control_rig_track
try:
    result = lib.find_or_create_control_rig_track(
        level_seq,
        cr_class if cr_class else cr_bp.generated_class(),
        face_binding)
    out.append(f"find_or_create result: {result}")
except Exception as e:
    out.append(f"find_or_create failed: {e}")
    # Try with just the binding
    try:
        # Maybe it takes world + level sequence
        world = unreal.EditorLevelLibrary.get_editor_world()
        result = lib.find_or_create_control_rig_track(
            world, level_seq, cr_class, face_binding)
        out.append(f"With world: {result}")
    except Exception as e2:
        out.append(f"With world also failed: {e2}")

# Check function signature
try:
    import inspect
    sig = inspect.signature(lib.find_or_create_control_rig_track)
    out.append(f"Signature: {sig}")
except:
    # Check help
    out.append(f"Help: check UE docs for find_or_create_control_rig_track params")

# Check what we have now
for b in level_seq.get_bindings():
    if b.get_display_name() == "Face":
        tracks = list(b.get_tracks())
        out.append(f"\nFace tracks: {len(tracks)}")
        for t in tracks:
            out.append(f"  {t.get_display_name()}")
            for s in t.get_sections():
                out.append(f"    Channels: {len(s.get_all_channels())}")

# Also check control rigs
rigs = lib.get_control_rigs(level_seq)
out.append(f"\nControl rigs: {len(rigs)}")
for r in rigs:
    out.append(f"  {r.control_rig.get_name()}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
