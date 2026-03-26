"""Check ALL tracks across ALL bindings for duplicates/orphans."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# Check all bindings and their tracks
for b in level_seq.get_bindings():
    bname = b.get_display_name()
    tracks = list(b.get_tracks())
    out.append(f"Binding: {bname} ({len(tracks)} tracks)")
    for t in tracks:
        tname = t.get_display_name()
        sections = t.get_sections()
        out.append(f"  Track: {tname} ({len(sections)} sections)")
        for s in sections:
            channels = s.get_all_channels()
            keyed = sum(1 for ch in channels if list(ch.get_keys()))
            out.append(f"    Channels: {len(channels)} total, {keyed} with keys")

# Also check root-level tracks (not under any binding)
root_tracks = level_seq.get_tracks()
if root_tracks:
    out.append(f"\nRoot-level tracks: {len(root_tracks)}")
    for t in root_tracks:
        out.append(f"  {t.get_display_name()}")

# Check control rigs
lib = unreal.ControlRigSequencerLibrary
rigs = lib.get_control_rigs(level_seq)
out.append(f"\nControl rigs: {len(rigs)}")
for r in rigs:
    out.append(f"  {r.control_rig.get_name()}")

# Scrub to frame 0 and check if face is at rest
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0)

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
