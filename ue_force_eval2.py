"""Check and fix sequencer evaluation."""
import unreal

out = []

# Check lock state
try:
    locked = unreal.LevelSequenceEditorBlueprintLibrary.is_level_sequence_locked()
    out.append(f"Locked: {locked}")
except Exception as e:
    out.append(f"Lock check: {e}")

# Lock it to enable evaluation
try:
    unreal.LevelSequenceEditorBlueprintLibrary.set_lock_level_sequence(True)
    out.append("Set locked = True")
except Exception as e:
    out.append(f"Set lock: {e}")

# Re-check
try:
    locked = unreal.LevelSequenceEditorBlueprintLibrary.is_level_sequence_locked()
    out.append(f"Now locked: {locked}")
except Exception as e:
    out.append(f"Re-check: {e}")

# Scrub to frame 10 to force evaluation
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(10 * 800)
out.append("Scrubbed to frame 10")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
