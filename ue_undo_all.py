"""Undo all recent changes by calling undo many times."""
import unreal

out = []
count = 0
for i in range(100):
    try:
        result = unreal.EditorLevelLibrary.editor_undo()
        count += 1
    except:
        break

out.append(f"Performed {count} undos")

# Scrub to frame 10 (PP) to check
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(10 * 800)
out.append("Scrubbed to frame 10 (PP)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
