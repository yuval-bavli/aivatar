"""Restore the Face_ControlBoard_CtrlRig track in the sequencer."""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
    world = unreal.EditorLevelLibrary.get_editor_world()
    p(f"World: {world.get_name()}")
    p(f"Sequence: {level_seq.get_name()}")

    # List current bindings
    p("\nCurrent bindings:")
    face_binding = None
    for binding in level_seq.get_bindings():
        name = binding.get_display_name()
        p(f"  {name} - tracks: {len(binding.get_tracks())}")
        if name == "Face":
            face_binding = binding

    # Check find_or_create_control_rig_track signature
    p(f"\n=== find_or_create_control_rig_track help ===")
    try:
        # Try calling with no args to see error message with signature
        lib.find_or_create_control_rig_track()
    except Exception as e:
        p(str(e))

    # Try to load the control rig class
    p("\n=== Loading CR class ===")

    # Try different paths
    paths = [
        "/Game/MetaHumans/model4/Face/Face_ControlBoard_CtrlRig",
        "/Game/MetaHumans/model4/Face/Face_ControlBoard_CtrlRig.Face_ControlBoard_CtrlRig_C",
        "/Game/MetaHumans/Common/Face/Face_ControlBoard_CtrlRig",
    ]

    cr_asset = None
    for path in paths:
        try:
            asset = unreal.load_asset(path)
            if asset:
                p(f"  {path} -> {type(asset).__name__}: {asset.get_name()}")
                cr_asset = asset
                break
            else:
                p(f"  {path} -> None")
        except Exception as e:
            p(f"  {path} -> Error: {e}")

    # Try using EditorAssetLibrary to find it
    if not cr_asset:
        p("\n=== Searching for Face_ControlBoard ===")
        try:
            assets = unreal.EditorAssetLibrary.list_assets("/Game/MetaHumans/", recursive=True)
            for a in assets:
                if 'ControlBoard' in a:
                    p(f"  {a}")
        except Exception as e:
            p(f"Search error: {e}")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
