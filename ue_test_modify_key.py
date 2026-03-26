"""Test if modifying an existing working key via set_value() changes the visual."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                # Find L_mouth_pressU - known to work at frame 10 with value 0.8
                if 'CTRL_L_mouth_pressU' in ch.get_name():
                    keys = list(ch.get_keys())
                    out.append(f"{ch.get_name()}: {len(keys)} keys")
                    for k in keys:
                        frame = k.get_time().frame_number.value
                        old = k.get_value()
                        if frame == 10:
                            # Change from 0.8 to 0.0 — PP lips should no longer be pressed
                            k.set_value(0.0)
                            out.append(f"  frame={frame}: {old:.2f} -> 0.00 (TEST)")
                        else:
                            out.append(f"  frame={frame}: {old:.2f}")
                    break
            break

# Scrub to PP
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(10)
out.append("\nScrubbed to frame 10 — check if PP lips are no longer pressed")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
