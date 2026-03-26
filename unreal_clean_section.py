"""Remove all keys from phantom channels to restore clean Control Rig evaluation."""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
face_track = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            face_track = track
            break
    if face_track: break

if not face_track:
    p("ERROR: Face track not found")
else:
    sections = face_track.get_sections()
    p(f"Face track has {len(sections)} sections")

    # Remove ALL sections - let the track be clean
    for sec in sections:
        face_track.remove_section(sec)
        p("Removed section")

    # Now add one fresh section
    new_sec = face_track.add_section()
    new_sec.set_start_frame_bounded(False)
    new_sec.set_end_frame_bounded(False)
    channels = new_sec.get_all_channels()

    # Verify no keys
    keyed = 0
    for ch in channels:
        try:
            if len(ch.get_keys()) > 0:
                keyed += 1
        except:
            pass

    p(f"New section: {len(channels)} channels, {keyed} with keys")
    p("Section should now be clean - scrub timeline to test")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
