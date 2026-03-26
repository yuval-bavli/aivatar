"""Test add_scalar_parameter_key and get_parameter_names."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

TICKS = 800

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]

            # Get parameter names
            try:
                names = section.get_parameter_names()
                out.append(f"Parameter names: {len(names)}")
                jaw_params = [n for n in names if 'jaw' in n.lower() or 'press' in n.lower()]
                out.append(f"Jaw/press params: {jaw_params}")
            except Exception as e:
                out.append(f"get_parameter_names error: {e}")

            # Try add_scalar_parameter_key
            try:
                # Check signature
                import inspect
                sig = str(inspect.signature(section.add_scalar_parameter_key))
                out.append(f"\nadd_scalar_parameter_key sig: {sig}")
            except:
                out.append("\nCouldn't get signature")

            # Try calling it
            try:
                result = section.add_scalar_parameter_key(
                    "CTRL_L_mouth_pressU",
                    unreal.FrameNumber(10 * TICKS),
                    0.8)
                out.append(f"add_scalar_parameter_key result: {result}")
            except Exception as e:
                out.append(f"add_scalar_parameter_key error: {e}")
                # Try with time_unit
                try:
                    result = section.add_scalar_parameter_key(
                        "CTRL_L_mouth_pressU",
                        unreal.FrameNumber(10),
                        0.8)
                    out.append(f"With frame 10 (display): {result}")
                except Exception as e2:
                    out.append(f"With frame 10 also failed: {e2}")

            # Also try add_vector2d_parameter_key for jaw
            try:
                sig = str(inspect.signature(section.add_vector2d_parameter_key))
                out.append(f"\nadd_vector2d_parameter_key sig: {sig}")
            except:
                pass

            try:
                result = section.add_vector2d_parameter_key(
                    "CTRL_C_jaw",
                    unreal.FrameNumber(30 * TICKS),
                    unreal.Vector2D(0, -1.0))
                out.append(f"add_vector2d_parameter_key result: {result}")
            except Exception as e:
                out.append(f"add_vector2d_parameter_key error: {e}")

            # Check keys created
            key_count = 0
            for ch in section.get_all_channels():
                if 'pressU' in ch.get_name() and 'CTRL_L' in ch.get_name():
                    keys = list(ch.get_keys())
                    key_count = len(keys)
                    out.append(f"\npressU channel keys: {key_count}")
                    for k in keys:
                        out.append(f"  frame={k.get_time().frame_number.value} val={k.get_value()}")
                    break

            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
