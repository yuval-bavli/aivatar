"""Dump actual key frame numbers for jaw_openExtreme."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                name = ch.get_name()
                if 'openExtreme' in name or ('jaw.Y' in name):
                    keys = list(ch.get_keys())
                    out.append(f"{name}: {len(keys)} keys")
                    for k in keys:
                        f = k.get_time().frame_number.value
                        v = k.get_value()
                        out.append(f"  tick={f} display={f/800:.1f} val={v:.4f}")
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
