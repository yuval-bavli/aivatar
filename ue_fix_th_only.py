"""
Fix ONLY the TH viseme (frame 30): open jaw and ensure tongue is visible.
Does NOT touch any other viseme frames.
"""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            break

if not face_section:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: Face section not found")
    raise SystemExit

# Find jaw.Y channel and fix ONLY frame 30
channels = face_section.get_all_channels()
for ch in channels:
    name = ch.get_name()
    if 'jaw.Y' in name and 'open' not in name.lower():
        keys = list(ch.get_keys())
        out.append(f"{name}: {len(keys)} keys")
        for k in keys:
            frame = k.get_time().frame_number.value
            if frame == 30:
                old_val = k.get_value()
                k.set_value(-0.5)
                out.append(f"  Frame 30 (TH): {old_val:.4f} -> -0.5000")
            else:
                out.append(f"  Frame {frame}: {k.get_value():.4f} (unchanged)")
        break

# Scrub to TH to see the result
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30 * 800)
out.append("\nScrubbed to frame 30 (TH)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
