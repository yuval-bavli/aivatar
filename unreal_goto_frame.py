"""Set sequencer to a specific frame."""
import unreal, sys

frame = int(sys.argv[1]) if len(sys.argv) > 1 else 50
TICKS = 800

try:
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)
    out = f"Set to frame {frame} (tick {frame*TICKS})"
except Exception as e:
    out = f"Error: {e}"

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out)
