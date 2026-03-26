"""Set sequencer to a specific frame and force update."""
import unreal
try: frame = VISEME_FRAME
except: frame = 0
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame / 30.0)
unreal.LevelSequenceEditorBlueprintLibrary.force_update()
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(f"Frame: {frame}")
