"""
Fix jaw.Y values by directly modifying channel key values.
The set_local_control_rig_vector2d API creates keys but doesn't set values properly.
"""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# Expected jaw.Y values per tick (tick = frame number since keys are at display rate)
jaw_y_values = {
    0: 0.0,       # sil
    10: -0.05,    # PP
    20: -0.15,    # FF
    30: -0.5,     # TH
    40: -0.35,    # DD
    50: -0.3,     # kk
    60: -0.15,    # CH
    70: -0.08,    # SS
    80: -0.15,    # nn
    90: -0.2,     # RR
    100: -0.8,    # aa (wide open)
    110: -0.4,    # E
    120: -0.15,   # ih
    130: -0.4,    # oh
    140: -0.15,   # ou
}

# Also tongue_tipMove.X values (all 0, but let's also handle tongue_tipMove.Y already done)

face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            break

if not face_section:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: Face section not found")
    raise SystemExit

channels = face_section.get_all_channels()
fixed = 0

for ch in channels:
    name = ch.get_name()

    if 'jaw.Y' in name and 'open' not in name.lower():
        keys = list(ch.get_keys())
        out.append(f"Fixing {name} ({len(keys)} keys)")
        for k in keys:
            tick = k.get_time().frame_number.value
            if tick in jaw_y_values:
                old_val = k.get_value()
                new_val = jaw_y_values[tick]
                # Try to set value on the key
                try:
                    k.set_value(float(new_val))
                    out.append(f"  tick={tick}: {old_val:.4f} -> {new_val:.4f}")
                    fixed += 1
                except Exception as e:
                    out.append(f"  tick={tick}: FAILED {e}")

out.append(f"\nFixed {fixed} jaw.Y keys")

# Verify
for ch in channels:
    name = ch.get_name()
    if 'jaw.Y' in name and 'open' not in name.lower():
        keys = list(ch.get_keys())
        out.append(f"\nVerify {name}:")
        for k in keys:
            tick = k.get_time().frame_number.value
            v = k.get_value()
            out.append(f"  tick={tick} val={v:.4f}")
        break

# Scrub to TH to see effect
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30 * 800)
out.append("\nScrubbed to frame 30 (TH)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
