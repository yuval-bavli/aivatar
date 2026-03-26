"""Verify what keys exist at frame 30 for TH-related controls."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                name = ch.get_name()
                # Check TH-related controls
                if any(x in name for x in ['jaw', 'openExtreme', 'tongue']):
                    keys = list(ch.get_keys())
                    if keys:
                        vals_at_30 = []
                        for k in keys:
                            f = k.get_time().frame_number.value
                            if f == 30:
                                vals_at_30.append(f"val={k.get_value()}")
                        if vals_at_30:
                            out.append(f"{name}: {', '.join(vals_at_30)} (total {len(keys)} keys)")
            break

out.append(f"\nTotal TH-related channels with keys at frame 30: {len([x for x in out if x])}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
