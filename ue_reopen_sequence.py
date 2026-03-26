"""Close and reopen the FaceExport level sequence to reset evaluation."""
import unreal

out = []

# Get current sequence path
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
seq_path = level_seq.get_path_name()
out.append(f"Current sequence: {seq_path}")

# Close the sequence editor
try:
    unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    out.append("Closed sequence editor")
except Exception as e:
    out.append(f"Close error: {e}")

# Reopen the sequence
try:
    seq_asset = unreal.load_asset(seq_path.split('.')[0])
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(seq_asset)
    out.append("Reopened sequence")
except Exception as e:
    out.append(f"Reopen error: {e}")

# Verify
level_seq2 = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
if level_seq2:
    out.append(f"Active sequence: {level_seq2.get_path_name()}")

    # Check keys
    for b in level_seq2.get_bindings():
        for t in b.get_tracks():
            if "Face_ControlBoard" in str(t.get_display_name()):
                section = t.get_sections()[0]
                keyed = sum(1 for ch in section.get_all_channels() if ch.get_num_keys() > 0)
                total = len(section.get_all_channels())
                out.append(f"Track: {total} channels, {keyed} with keys")
                break
else:
    out.append("No active sequence after reopen")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
