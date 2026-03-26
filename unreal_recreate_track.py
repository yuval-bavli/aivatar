"""
Recreate the Face Control Rig track from scratch using the proper API.
Then check what the original _0 channels look like.
"""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

    # First check current section's parameter names
    face_track = None
    face_binding = None
    for binding in level_seq.get_bindings():
        for track in binding.get_tracks():
            if "Face_ControlBoard" in str(track.get_display_name()):
                face_track = track
                face_binding = binding
                break
        if face_track: break

    if face_track:
        sections = face_track.get_sections()
        if sections:
            sec = sections[0]
            try:
                params = sec.get_parameter_names()
                p(f"Current section parameter names: {len(params)}")
                for pn in params[:10]:
                    p(f"  {pn}")
                if len(params) > 10:
                    p(f"  ... and {len(params)-10} more")
            except Exception as e:
                p(f"get_parameter_names error: {e}")
        else:
            p("No sections in face track")

        # Remove the face track entirely
        face_binding.remove_track(face_track)
        p("\nRemoved Face_ControlBoard track")

    # Now use find_or_create_control_rig_track to recreate it
    p("\n=== Recreating track with find_or_create_control_rig_track ===")
    try:
        # Load the control rig class
        cr_class = unreal.load_object(unreal.ControlRigBlueprint,
            "/Game/MetaHumans/model4/Face/Face_ControlBoard_CtrlRig")
        p(f"CR Blueprint: {cr_class.get_name()}")
    except Exception as e:
        p(f"Load CR blueprint error: {e}")

    # Try to find the binding for the Face skeletal mesh
    p(f"\nAll bindings:")
    for binding in level_seq.get_bindings():
        p(f"  {binding.get_display_name()} ({binding.get_id()})")

    # Try find_or_create using the binding
    try:
        result = lib.find_or_create_control_rig_track(
            level_sequence=level_seq,
            control_rig_class=unreal.load_class(None,
                "/Game/MetaHumans/model4/Face/Face_ControlBoard_CtrlRig.Face_ControlBoard_CtrlRig_C"),
            binding=face_binding
        )
        p(f"find_or_create result: {result}")
    except Exception as e:
        p(f"find_or_create error: {e}")
        p(traceback.format_exc())

    # Alternative: try with just ControlRig class
    try:
        p("\n=== Trying with unreal.ControlRig class path ===")
        # Get the generated class from the blueprint
        cr_bp = unreal.load_asset("/Game/MetaHumans/model4/Face/Face_ControlBoard_CtrlRig")
        p(f"Loaded asset: {cr_bp} ({type(cr_bp).__name__})")
        if hasattr(cr_bp, 'generated_class'):
            p(f"Generated class: {cr_bp.generated_class()}")
    except Exception as e:
        p(f"Alt approach error: {e}")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
