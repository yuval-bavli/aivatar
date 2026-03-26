"""Close and reopen the level sequence to force rebinding."""
import unreal

out = []

# Get current sequence path
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
seq_path = level_seq.get_path_name()
out.append(f"Sequence: {seq_path}")

# Close it
unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
out.append("Closed sequence")

# Reopen it
seq_asset = unreal.load_asset(seq_path.split('.')[0])
unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(seq_asset)
out.append("Reopened sequence")

# Lock and scrub
unreal.LevelSequenceEditorBlueprintLibrary.set_lock_level_sequence(True)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(10 * 800)
out.append("Locked and scrubbed to frame 10 (PP)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
