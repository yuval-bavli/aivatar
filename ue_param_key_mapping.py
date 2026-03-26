"""Figure out the exact frame number mapping for add_scalar_parameter_key."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]

            # Clear existing
            for ch in section.get_all_channels():
                if 'openExtreme' in ch.get_name():
                    for k in reversed(list(ch.get_keys())):
                        ch.remove_key(k)
                    break

            # Test various input values
            test_values = [
                (30, 0.1),           # display frame 30?
                (24000, 0.2),        # 30 * 800 ticks
                (30 * 800, 0.3),     # same as 24000
                (100, 0.4),          # display frame 100?
            ]

            for fn_val, scalar_val in test_values:
                section.add_scalar_parameter_key(
                    "CTRL_C_jaw_openExtreme",
                    unreal.FrameNumber(fn_val),
                    scalar_val)
                out.append(f"Input: FrameNumber({fn_val}), val={scalar_val}")

            # Dump results
            for ch in section.get_all_channels():
                if 'openExtreme' in ch.get_name():
                    keys = list(ch.get_keys())
                    out.append(f"\n{ch.get_name()}: {len(keys)} keys")
                    for k in keys:
                        f = k.get_time().frame_number.value
                        v = k.get_value()
                        out.append(f"  stored_tick={f} (display={f/800:.2f}) val={v:.4f}")
                    break
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
