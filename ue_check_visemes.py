"""
Scrub to specific viseme frames and capture close-up screenshots.
"""
import unreal

# First scrub to TH (frame 30) for screenshot
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30 * 800)

# Also read back jaw values to confirm they're actually applied
out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# Get face section and read jaw.Y keys
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            channels = section.get_all_channels()
            for ch in channels:
                name = ch.get_name()
                if 'jaw' in name.lower() or 'tongue' in name.lower():
                    keys = list(ch.get_keys())
                    if keys:
                        out.append(f"{name}: {len(keys)} keys")
                        for k in keys:
                            f = k.get_time().frame_number.value
                            v = k.get_value()
                            out.append(f"  tick={f} frame={f//800} val={v:.3f}")
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
