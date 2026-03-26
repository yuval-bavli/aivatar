"""Force sequencer evaluation and check bound objects."""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# Check bound objects for each binding
for binding in level_seq.get_bindings():
    bname = binding.get_display_name()
    try:
        bound = unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(binding)
        p(f"Binding '{bname}' -> {len(bound)} bound objects")
        for obj in bound:
            p(f"  {obj.get_name()} ({type(obj).__name__})")
    except Exception as e:
        p(f"Binding '{bname}' -> error: {e}")

# Set to frame 100 and force update
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(100.0/30.0)
p(f"\nSet to frame 100")

try:
    unreal.LevelSequenceEditorBlueprintLibrary.force_update()
    p("force_update() -> OK")
except Exception as e:
    p(f"force_update error: {e}")

# Also try refresh
try:
    unreal.LevelSequenceEditorBlueprintLibrary.refresh_current_level_sequence()
    p("refresh_current_level_sequence() -> OK")
except Exception as e:
    p(f"refresh error: {e}")

p(f"\nCurrent time: {unreal.LevelSequenceEditorBlueprintLibrary.get_current_time()}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
