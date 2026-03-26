"""List ALL channels that have keys, showing channel names and key count."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            channels_with_keys = []
            channels_without = []
            for ch in section.get_all_channels():
                name = ch.get_name()
                keys = list(ch.get_keys())
                if keys:
                    channels_with_keys.append(f"  {name}: {len(keys)} keys")
                else:
                    channels_without.append(name)

            out.append(f"Channels WITH keys ({len(channels_with_keys)}):")
            out.extend(channels_with_keys)
            out.append(f"\nChannels WITHOUT keys: {len(channels_without)}")
            # Show channels without keys that contain tongue or jaw
            jaw_tongue = [n for n in channels_without if 'jaw' in n.lower() or 'tongue' in n.lower() or 'open' in n.lower()]
            out.append(f"Jaw/tongue/open channels without keys:")
            for n in jaw_tongue:
                out.append(f"  {n}")
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
