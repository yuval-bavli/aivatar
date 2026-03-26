"""Fix TH jaw opening by modifying the jaw_openExtreme channel key directly."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                if 'openExtreme' in ch.get_name():
                    keys = list(ch.get_keys())
                    out.append(f"{ch.get_name()}: {len(keys)} keys")
                    for k in keys:
                        frame = k.get_time().frame_number.value
                        old = k.get_value()
                        if frame == 30:
                            k.set_value(1.0)
                            out.append(f"  frame={frame}: {old:.2f} -> 1.00")
                        else:
                            out.append(f"  frame={frame}: {old:.2f} (unchanged)")
                    break
            break

# Scrub to TH
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30)
out.append("\nScrubbed to frame 30")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
