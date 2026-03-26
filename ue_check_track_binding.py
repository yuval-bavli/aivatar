"""Check if the face control rig track is properly bound."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    if b.get_display_name() == "Face":
        out.append(f"Face binding ID: {b.get_id()}")
        # Check binding properties
        props = dir(b)
        out.append(f"Binding props: {[p for p in props if not p.startswith('_')][:20]}")

        for t in b.get_tracks():
            out.append(f"\nTrack: {t.get_display_name()}")
            out.append(f"Track type: {type(t).__name__}")

            # Check track properties
            try:
                cr_class = t.get_editor_property("control_rig_class")
                out.append(f"control_rig_class: {cr_class}")
            except Exception as e:
                out.append(f"control_rig_class: {e}")

            try:
                section = t.get_sections()[0]
                out.append(f"Section type: {type(section).__name__}")
                # Check section properties
                try:
                    cr_ref = section.get_editor_property("control_rig")
                    out.append(f"section.control_rig: {cr_ref}")
                except:
                    pass
                try:
                    cr_class2 = section.get_editor_property("control_rig_class")
                    out.append(f"section.control_rig_class: {cr_class2}")
                except:
                    pass
            except Exception as e:
                out.append(f"Section error: {e}")

# Compare with Body binding (which works)
for b in level_seq.get_bindings():
    if b.get_display_name() == "Body":
        for t in b.get_tracks():
            out.append(f"\n--- Body track for comparison ---")
            out.append(f"Track: {t.get_display_name()}")
            try:
                cr_class = t.get_editor_property("control_rig_class")
                out.append(f"control_rig_class: {cr_class}")
            except Exception as e:
                out.append(f"control_rig_class: {e}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
