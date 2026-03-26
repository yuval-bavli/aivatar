"""Read back jaw.Y channel values immediately after keying."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            channels = section.get_all_channels()
            for ch in channels:
                name = ch.get_name()
                keys = list(ch.get_keys())
                if keys:
                    out.append(f"{name}: {len(keys)} keys")
                    for k in keys:
                        tick = k.get_time().frame_number.value
                        v = k.get_value()
                        out.append(f"  tick={tick} val={v:.4f}")
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
