"""Check tongue channel values and try boosting them."""
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

channels = face_section.get_all_channels()

p("=== ALL TONGUE CHANNELS ===")
for ch in channels:
    n = ch.get_name()
    if "tongue" in n.lower():
        try:
            nk = ch.get_num_keys()
        except:
            nk = "?"
        p(f"  {n} [{nk} keys]")
        if nk and nk != "?" and nk > 0:
            for k in ch.get_keys():
                fv = k.get_time().frame_number.value
                val = k.get_value()
                if val != 0:
                    p(f"    frame={fv}, val={val}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
