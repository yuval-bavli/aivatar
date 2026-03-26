"""Check jaw-related channel keys."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                name = ch.get_name()
                if 'jaw' in name.lower() or 'tongue' in name.lower() or 'open' in name.lower():
                    keys = list(ch.get_keys())
                    if keys:
                        out.append(f"\n{name}: {len(keys)} keys")
                        for k in keys:
                            f = k.get_time().frame_number.value
                            v = k.get_value()
                            if abs(v) > 0.001:
                                out.append(f"  frame_tick={f} (display={f//800}) val={v:.4f}")
                    else:
                        out.append(f"{name}: 0 keys")
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
