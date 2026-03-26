"""Check if Face binding is properly connected to the actor component."""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

    for binding in level_seq.get_bindings():
        name = binding.get_display_name()
        p(f"\n=== Binding: {name} ===")
        p(f"  ID: {binding.get_id()}")

        try:
            bound = binding.get_bound_objects()
            p(f"  Bound objects: {len(bound)}")
            for obj in bound:
                p(f"    {obj.get_name()} ({type(obj).__name__})")
        except Exception as e:
            p(f"  get_bound_objects error: {e}")

        try:
            parent = binding.get_parent()
            if parent:
                p(f"  Parent: {parent.get_display_name()}")
        except: pass

        try:
            children = binding.get_child_possessables()
            p(f"  Children: {len(children)}")
            for ch in children:
                p(f"    {ch.get_display_name()}")
        except: pass

        tracks = binding.get_tracks()
        for t in tracks:
            p(f"  Track: {t.get_display_name()} ({type(t).__name__})")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
