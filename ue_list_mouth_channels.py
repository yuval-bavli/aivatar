"""List all mouth/lip related channel names."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                name = ch.get_name()
                if 'mouth' in name.lower() or 'lip' in name.lower() or 'jaw' in name.lower():
                    out.append(name)
            break

out.sort()
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
