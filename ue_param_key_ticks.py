"""Test add_scalar_parameter_key with tick values (frame * 800)."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

TICKS = 800

# Clear existing keys first
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]

            # Clear jaw_openExtreme keys
            for ch in section.get_all_channels():
                if 'openExtreme' in ch.get_name():
                    for k in reversed(list(ch.get_keys())):
                        ch.remove_key(k)
                    out.append(f"Cleared {ch.get_name()}")
                    break

            # Test with different frame number approaches
            # Approach 1: FrameNumber(30 * 800) - ticks
            try:
                section.add_scalar_parameter_key(
                    "CTRL_C_jaw_openExtreme",
                    unreal.FrameNumber(30 * TICKS),
                    1.0)
                out.append("Keyed with FrameNumber(30*800)")
            except Exception as e:
                out.append(f"Ticks failed: {e}")

            # Approach 2: FrameNumber(100 * 800) - ticks
            try:
                section.add_scalar_parameter_key(
                    "CTRL_C_jaw_openExtreme",
                    unreal.FrameNumber(100 * TICKS),
                    0.3)
                out.append("Keyed with FrameNumber(100*800)")
            except Exception as e:
                out.append(f"Ticks 100 failed: {e}")

            # Check where keys landed
            for ch in section.get_all_channels():
                if 'openExtreme' in ch.get_name():
                    keys = list(ch.get_keys())
                    out.append(f"\n{ch.get_name()}: {len(keys)} keys")
                    for k in keys:
                        f = k.get_time().frame_number.value
                        v = k.get_value()
                        out.append(f"  tick={f} display={f/800:.1f} val={v:.4f}")
                    break
            break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
