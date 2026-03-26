"""Check section state: is_active, blend_type, completion_mode, range."""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
face_section = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            sections = track.get_sections()
            if sections:
                face_section = sections[0]
                break
    if face_section: break

p(f"is_active: {face_section.is_active()}")
p(f"is_locked: {face_section.is_locked()}")
p(f"blend_type: {face_section.get_blend_type()}")
p(f"completion_mode: {face_section.get_completion_mode()}")
p(f"has_start_frame: {face_section.has_start_frame()}")
p(f"has_end_frame: {face_section.has_end_frame()}")
try: p(f"start_frame: {face_section.get_start_frame()}")
except: p("start_frame: (none)")
try: p(f"end_frame: {face_section.get_end_frame()}")
except: p("end_frame: (none)")

# Check current sequencer time
p(f"\ncurrent_time: {unreal.LevelSequenceEditorBlueprintLibrary.get_current_time()}")
p(f"playback_start: {unreal.LevelSequenceEditorBlueprintLibrary.get_playback_start_position()}")
p(f"playback_end: {unreal.LevelSequenceEditorBlueprintLibrary.get_playback_end_position()}")

# Check if the section has the right ControlRig reference
p(f"\n=== Section properties ===")
for prop in ['control_rig', 'ControlRig', 'control_rig_class']:
    try:
        val = face_section.get_editor_property(prop)
        p(f"{prop}: {val}")
    except:
        pass

# Check ALL editor properties
p(f"\n=== All section editor properties ===")
try:
    # List properties by trying common ones
    for prop in ['weight', 'active', 'locked', 'blend_type', 'completion_mode',
                 'row_index', 'overlap_priority', 'pre_roll_frames', 'post_roll_frames',
                 'color_tint']:
        try:
            val = face_section.get_editor_property(prop)
            p(f"  {prop}: {val}")
        except:
            pass
except:
    pass

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
