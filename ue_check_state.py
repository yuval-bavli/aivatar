"""Check current state of face section channels."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

if not level_seq:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: No sequence")
    raise SystemExit

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            sections = t.get_sections()
            out.append(f"Track: {t.get_display_name()}, sections: {len(sections)}")
            section = sections[0]
            channels = section.get_all_channels()
            out.append(f"Total channels: {len(channels)}")
            keyed_channels = 0
            for ch in channels:
                keys = list(ch.get_keys())
                if keys:
                    keyed_channels += 1
                    out.append(f"  {ch.get_name()}: {len(keys)} keys")
            out.append(f"Channels with keys: {keyed_channels}")
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
