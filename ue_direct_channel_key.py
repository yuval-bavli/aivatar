"""Try adding keys directly to channels instead of via set_local_control_rig_float."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

TICKS = 800

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                name = ch.get_name()
                if 'CTRL_L_mouth_pressU' in name:
                    out.append(f"Channel: {name}")
                    out.append(f"Type: {type(ch)}")

                    # List available methods
                    methods = [m for m in dir(ch) if not m.startswith('_') and 'key' in m.lower() or 'add' in m.lower()]
                    out.append(f"Key/Add methods: {methods}")

                    # Try add_key
                    try:
                        frame_num = unreal.FrameNumber(10 * TICKS)
                        new_key = ch.add_key(frame_num, 0.8)
                        out.append(f"add_key result: {new_key}")
                    except Exception as e:
                        out.append(f"add_key(FrameNumber, float) failed: {e}")

                    # Try with time
                    try:
                        time = unreal.FrameTime(unreal.FrameNumber(10 * TICKS))
                        new_key = ch.add_key(time, 0.8)
                        out.append(f"add_key(FrameTime, float) result: {new_key}")
                    except Exception as e:
                        out.append(f"add_key(FrameTime, float) failed: {e}")

                    keys_after = len(list(ch.get_keys()))
                    out.append(f"Keys after attempts: {keys_after}")
                    break
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
