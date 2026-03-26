"""Check for duplicate channels and which ones have keys."""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
face_section = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            sections = track.get_sections()
            if sections:
                face_section = sections[0]
                break
    if face_section: break

channels = face_section.get_all_channels()
p(f"Total channels: {len(channels)}")

# Group channels by base name (strip trailing _N suffix)
import re
groups = {}
for ch in channels:
    name = ch.get_name()
    # Strip trailing _N where N is a digit
    base = re.sub(r'_(\d+)$', '', name)
    if base not in groups:
        groups[base] = []
    try:
        nk = ch.get_num_keys()
    except:
        nk = 0
    groups[base].append((name, nk))

# Show groups with duplicates (more than 1 channel per base name)
p(f"\n=== DUPLICATE CHANNELS (jaw/mouth/tongue only) ===")
for base in sorted(groups.keys()):
    entries = groups[base]
    bl = base.lower()
    if not ("jaw" in bl or "mouth" in bl or "tongue" in bl or "lip" in bl):
        continue
    if len(entries) > 1:
        p(f"\n{base}: {len(entries)} versions")
        for name, nk in entries:
            p(f"  {name} [{nk} keys]")

# Show which suffix has the keys for jaw.Y
p(f"\n=== CTRL_C_jaw.Y versions ===")
for ch in channels:
    name = ch.get_name()
    if "CTRL_C_jaw.Y" in name:
        try:
            nk = ch.get_num_keys()
            keys = ch.get_keys()
            p(f"{name}: {nk} keys")
            for k in keys[:3]:
                p(f"  frame={k.get_time().frame_number.value}, val={k.get_value():.3f}")
            if nk > 3:
                p(f"  ... ({nk-3} more)")
        except:
            p(f"{name}: error reading keys")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
