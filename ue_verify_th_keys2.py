"""Verify what keys exist for TH-related controls - check ALL frame numbers."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                name = ch.get_name()
                if any(x in name for x in ['openExtreme', 'tongue_inOut', 'tongue_press', 'tongue_tip']):
                    keys = list(ch.get_keys())
                    if keys:
                        out.append(f"{name}: {len(keys)} keys")
                        for k in keys:
                            f = k.get_time().frame_number.value
                            v = k.get_value()
                            out.append(f"  frame_num={f} (display={f//800}) val={v}")
            break

if not out:
    out.append("No tongue/openExtreme channels found with keys")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
