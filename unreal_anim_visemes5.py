"""Add start_frame parameter and fix sequence length issue."""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    anim_seq = unreal.load_asset("/Game/Aivatar/VisemePoses")
    p(f"Anim length: {anim_seq.sequence_length}s, num_frames: {anim_seq.number_of_frames}")

    # The sequence length is wrong (0.033s). The keys at frame 140/30 = 4.667s
    # but it shows 0.033s. This means the keys were stored at time=0 to time=0.033
    # because 1/30 = 0.033. Frame 1 at 1/30 seconds.
    # The issue: all 15 visemes keys are at frames 0-14 (0/30 to 14/30 seconds)
    # but we want frames 0-140.
    # The add_float_curve_key times were: 0/30, 10/30, 20/30... 140/30
    # = 0, 0.333, 0.667, 1.0, ... 4.667 seconds
    # But length shows 0.033. That means the keys might have been placed wrong.
    # Let me check the actual keys

    anim_lib = unreal.AnimationLibrary
    try:
        keys = anim_lib.get_float_keys(anim_seq, "CTRL_C_jaw_openExtreme")
        p(f"jaw_openExtreme keys: {len(keys)}")
        for k in keys:
            p(f"  time={k} ({type(k).__name__})")
    except Exception as e:
        p(f"get_float_keys error: {e}")

    # The sequence length 0.033 = 1 frame at 30fps. Maybe AnimSequence
    # doesn't auto-extend from curve keys. Let me set number_of_frames.
    try:
        # Try setting via number_of_frames or number_of_sampled_keys
        for attr in dir(anim_seq):
            if 'frame' in attr.lower() or 'sample' in attr.lower() or 'number' in attr.lower():
                if not attr.startswith('_'):
                    try:
                        val = getattr(anim_seq, attr)
                        if not callable(val):
                            p(f"  {attr} = {val}")
                    except: pass
    except: pass

    # Try set_editor_property for number_of_sampled_keys
    try:
        anim_seq.set_editor_property('number_of_sampled_keys', 151)
        p("Set number_of_sampled_keys = 151")
    except Exception as e:
        p(f"set number_of_sampled_keys error: {e}")

    # Try number_of_frames
    try:
        anim_seq.set_editor_property('number_of_frames', 150)
        p("Set number_of_frames = 150")
    except Exception as e:
        p(f"set number_of_frames error: {e}")

    p(f"After: length={anim_seq.sequence_length}s, frames={anim_seq.number_of_frames}")

    # Now try loading with start_frame
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

    face_track = None
    for binding in level_seq.get_bindings():
        for track in binding.get_tracks():
            if "Face_ControlBoard" in str(track.get_display_name()):
                face_track = track
                break
        if face_track: break

    # Find face mesh comp
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

    try:
        lib.load_anim_sequence_into_control_rig_section(
            sec, anim_seq, face_mesh_comp, unreal.FrameNumber(0))
        p("\nload_anim_sequence_into_control_rig_section OK!")
    except Exception as e:
        p(f"\nload error: {e}")

    # Check keyed channels
    keyed = 0
    for ch in sec.get_all_channels():
        keys = ch.get_keys()
        if len(keys) > 0:
            keyed += 1
            name = ch.get_name()
            if keyed <= 10:
                vals = [(round(k.get_time().frame_number.value/800), round(k.get_value(),3)) for k in keys[:4]]
                p(f"  {name}: {vals}")
    p(f"Total keyed: {keyed}/{len(sec.get_all_channels())}")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
