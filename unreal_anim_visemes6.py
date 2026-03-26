"""Simplified: just load the anim with all required args."""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    anim_seq = unreal.load_asset("/Game/Aivatar/VisemePoses")
    p(f"Anim length: {anim_seq.sequence_length}s")

    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

    face_track = None
    for binding in level_seq.get_bindings():
        for track in binding.get_tracks():
            if "Face_ControlBoard" in str(track.get_display_name()):
                face_track = track
                break
        if face_track: break

    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    face_mesh_comp = None
    for actor in actors:
        if 'bp_model4' in actor.get_name().lower():
            for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
                if comp.get_name() == "Face":
                    face_mesh_comp = comp
                    break
            break

    sec = face_track.get_sections()[0]

    # Try with all positional args
    try:
        lib.load_anim_sequence_into_control_rig_section(
            sec, anim_seq, face_mesh_comp, unreal.FrameNumber(0))
        p("load OK!")
    except Exception as e:
        p(f"Attempt 1: {e}")

    # Try with keyword args
    try:
        lib.load_anim_sequence_into_control_rig_section(
            movie_scene_section=sec,
            anim_sequence=anim_seq,
            skel_mesh_comp=face_mesh_comp,
            start_frame=unreal.FrameNumber(0)
        )
        p("Attempt 2 OK!")
    except Exception as e:
        p(f"Attempt 2: {e}")

    # Try with more args (maybe needs end_frame too)
    try:
        lib.load_anim_sequence_into_control_rig_section(
            sec, anim_seq, face_mesh_comp, unreal.FrameNumber(0),
            unreal.FrameNumber(150 * 800)
        )
        p("Attempt 3 OK!")
    except Exception as e:
        p(f"Attempt 3: {e}")

    # Use the with_range version
    try:
        lib.load_anim_sequence_into_control_rig_section_with_range(
            sec, anim_seq, face_mesh_comp,
            unreal.FrameNumber(0), unreal.FrameNumber(150 * 800)
        )
        p("with_range OK!")
    except Exception as e:
        p(f"with_range: {e}")

    # Check keyed channels
    keyed = 0
    for ch in sec.get_all_channels():
        keys = ch.get_keys()
        if len(keys) > 0:
            keyed += 1
            name = ch.get_name()
            if keyed <= 5:
                vals = [(round(k.get_time().frame_number.value/800), round(k.get_value(),3)) for k in keys[:4]]
                p(f"  {name}: {vals}")
    p(f"Total keyed: {keyed}/{len(sec.get_all_channels())}")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
