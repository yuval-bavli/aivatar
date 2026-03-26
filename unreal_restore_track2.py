"""Restore Face_ControlBoard_CtrlRig track using find_or_create_control_rig_track."""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
    world = unreal.EditorLevelLibrary.get_editor_world()

    # Get Face binding
    face_binding = None
    for binding in level_seq.get_bindings():
        if binding.get_display_name() == "Face":
            face_binding = binding
            break
    p(f"Face binding: {face_binding.get_display_name()}")

    # Load CR blueprint and get generated class
    cr_bp = unreal.load_asset("/Game/MetaHumans/Common/Face/Face_ControlBoard_CtrlRig")
    p(f"CR Blueprint: {cr_bp.get_name()} ({type(cr_bp).__name__})")

    # Try to get the generated class
    gen_class = None
    for attr in dir(cr_bp):
        if 'class' in attr.lower() and 'generated' in attr.lower():
            p(f"  Found attr: {attr}")
            try:
                gen_class = getattr(cr_bp, attr)
                if callable(gen_class):
                    gen_class = gen_class()
                p(f"  Generated class: {gen_class}")
            except Exception as e:
                p(f"  Error: {e}")

    # Try loading the _C class directly
    try:
        cr_class = unreal.load_class(None, "/Game/MetaHumans/Common/Face/Face_ControlBoard_CtrlRig.Face_ControlBoard_CtrlRig_C")
        p(f"CR Class via load_class: {cr_class}")
    except Exception as e:
        p(f"load_class error: {e}")
        cr_class = None

    # Try find_or_create with different arg combinations
    p("\n=== Trying find_or_create_control_rig_track ===")

    # Attempt 1: world, level_seq, cr_class, binding
    try:
        result = lib.find_or_create_control_rig_track(
            world, level_seq, cr_class, face_binding
        )
        p(f"Attempt 1 OK: {result}")
    except Exception as e:
        p(f"Attempt 1: {e}")

    # Attempt 2: world, level_seq, cr_bp, binding
    try:
        result = lib.find_or_create_control_rig_track(
            world, level_seq, cr_bp, face_binding
        )
        p(f"Attempt 2 OK: {result}")
    except Exception as e:
        p(f"Attempt 2: {e}")

    # Attempt 3: keyword args
    try:
        result = lib.find_or_create_control_rig_track(
            world=world,
            level_sequence=level_seq,
            control_rig_class=cr_class,
            binding=face_binding
        )
        p(f"Attempt 3 OK: {result}")
    except Exception as e:
        p(f"Attempt 3: {e}")

    # Attempt 4: just world and class
    try:
        result = lib.find_or_create_control_rig_track(world, level_seq, cr_class)
        p(f"Attempt 4 OK: {result}")
    except Exception as e:
        p(f"Attempt 4: {e}")

    # Check final state
    p("\n=== Final state ===")
    for binding in level_seq.get_bindings():
        name = binding.get_display_name()
        tracks = binding.get_tracks()
        p(f"  {name}: {len(tracks)} tracks")
        for t in tracks:
            p(f"    {t.get_display_name()}")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
