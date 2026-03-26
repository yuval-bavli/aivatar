"""Check remaining channels and scrub to sil to verify face looks normal."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            channels = section.get_all_channels()
            out.append(f"Total channels: {len(channels)}")
            keyed = 0
            for ch in channels:
                keys = list(ch.get_keys())
                if keys:
                    keyed += 1
                    out.append(f"  {ch.get_name()}: {len(keys)} keys")
                    for k in keys[:3]:
                        out.append(f"    frame={k.get_time().frame_number.value} val={k.get_value():.4f}")
            out.append(f"Channels with keys: {keyed}")
            break

# Scrub to frame 0 (sil/rest pose)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
out.append("\nScrubbed to frame 0 (sil)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
