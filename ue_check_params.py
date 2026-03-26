"""Check if the control rig section has registered parameters."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            out.append(f"Section type: {type(section)}")

            # Check section methods
            methods = [m for m in dir(section) if not m.startswith('_')]
            param_methods = [m for m in methods if 'param' in m.lower() or 'scalar' in m.lower() or 'control' in m.lower()]
            out.append(f"Param methods: {param_methods}")

            # Try get_scalar_parameter_names
            try:
                names = section.get_scalar_parameter_names()
                out.append(f"Scalar params: {len(names)}")
                mouth_params = [n for n in names if 'mouth' in n.lower() or 'jaw' in n.lower()]
                out.append(f"Mouth/jaw params: {mouth_params[:10]}")
            except Exception as e:
                out.append(f"get_scalar_parameter_names error: {e}")

            # Try has_scalar_parameter
            try:
                has = section.has_scalar_parameter("CTRL_L_mouth_pressU")
                out.append(f"has_scalar_parameter('CTRL_L_mouth_pressU'): {has}")
            except Exception as e:
                out.append(f"has_scalar_parameter error: {e}")

            # Check if add_scalar_parameter exists
            add_methods = [m for m in methods if 'add' in m.lower()]
            out.append(f"Add methods: {add_methods}")

            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
