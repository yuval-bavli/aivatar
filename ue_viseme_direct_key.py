"""
Key 15 Azure viseme poses using DIRECT channel key addition.
set_local_control_rig_float is broken, so we add keys directly to channels.
"""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

if not level_seq:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: No level sequence open")
    raise SystemExit

TICKS = 800

# Viseme data: frame -> (name, {control: value})
# For vec2d controls like CTRL_C_jaw, use separate .X and .Y entries
visemes = [
    (0, "sil", {
        "CTRL_C_jaw.Y": 0.0,
    }),
    (10, "PP", {
        "CTRL_C_jaw.Y": -0.05,
        "CTRL_L_mouth_pressU": 0.8, "CTRL_R_mouth_pressU": 0.8,
        "CTRL_L_mouth_pressD": 0.8, "CTRL_R_mouth_pressD": 0.8,
        "CTRL_L_mouth_tightenU": 0.5, "CTRL_R_mouth_tightenU": 0.5,
        "CTRL_L_mouth_tightenD": 0.5, "CTRL_R_mouth_tightenD": 0.5,
    }),
    (20, "FF", {
        "CTRL_C_jaw.Y": -0.15,
        "CTRL_L_mouth_lipsRollD": 0.7, "CTRL_R_mouth_lipsRollD": 0.7,
        "CTRL_L_mouth_lipBiteU": 0.6, "CTRL_R_mouth_lipBiteU": 0.6,
        "CTRL_L_mouth_upperLipRaise": 0.2, "CTRL_R_mouth_upperLipRaise": 0.2,
    }),
    (30, "TH", {
        "CTRL_C_jaw.Y": -1.5,
        "CTRL_C_jaw_openExtreme": 1.0,
        "CTRL_C_tongue_inOut": 0.9,
        "CTRL_C_tongue_tipMove.Y": 0.4,
        "CTRL_L_mouth_upperLipRaise": 0.5, "CTRL_R_mouth_upperLipRaise": 0.5,
        "CTRL_L_mouth_lowerLipDepress": 0.6, "CTRL_R_mouth_lowerLipDepress": 0.6,
        "CTRL_L_mouth_lipsTowardsTeethD": 0.5, "CTRL_R_mouth_lipsTowardsTeethD": 0.5,
    }),
    (40, "DD", {
        "CTRL_C_jaw.Y": -0.35,
        "CTRL_C_tongue_press": 0.5,
    }),
    (50, "kk", {
        "CTRL_C_jaw.Y": -0.3,
    }),
    (60, "CH", {
        "CTRL_C_jaw.Y": -0.15,
        "CTRL_L_mouth_funnelU": 0.6, "CTRL_R_mouth_funnelU": 0.6,
        "CTRL_L_mouth_funnelD": 0.6, "CTRL_R_mouth_funnelD": 0.6,
        "CTRL_L_mouth_purseU": 0.3, "CTRL_R_mouth_purseU": 0.3,
        "CTRL_L_mouth_purseD": 0.3, "CTRL_R_mouth_purseD": 0.3,
        "CTRL_L_mouth_tightenU": 0.3, "CTRL_R_mouth_tightenU": 0.3,
        "CTRL_L_mouth_tightenD": 0.3, "CTRL_R_mouth_tightenD": 0.3,
    }),
    (70, "SS", {
        "CTRL_C_jaw.Y": -0.08,
        "CTRL_L_mouth_stretch": 0.5, "CTRL_R_mouth_stretch": 0.5,
    }),
    (80, "nn", {
        "CTRL_C_jaw.Y": -0.15,
        "CTRL_C_tongue_press": 0.4,
    }),
    (90, "RR", {
        "CTRL_C_jaw.Y": -0.2,
        "CTRL_L_mouth_funnelU": 0.3, "CTRL_R_mouth_funnelU": 0.3,
        "CTRL_L_mouth_funnelD": 0.3, "CTRL_R_mouth_funnelD": 0.3,
    }),
    (100, "aa", {
        "CTRL_C_jaw.Y": -0.8,
        "CTRL_C_jaw_openExtreme": 0.3,
    }),
    (110, "E", {
        "CTRL_C_jaw.Y": -0.4,
        "CTRL_L_mouth_stretch": 0.4, "CTRL_R_mouth_stretch": 0.4,
        "CTRL_L_mouth_cornerPull": 0.15, "CTRL_R_mouth_cornerPull": 0.15,
    }),
    (120, "ih", {
        "CTRL_C_jaw.Y": -0.15,
        "CTRL_L_mouth_stretch": 0.6, "CTRL_R_mouth_stretch": 0.6,
        "CTRL_L_mouth_cornerPull": 0.3, "CTRL_R_mouth_cornerPull": 0.3,
    }),
    (130, "oh", {
        "CTRL_C_jaw.Y": -0.4,
        "CTRL_L_mouth_funnelU": 0.6, "CTRL_R_mouth_funnelU": 0.6,
        "CTRL_L_mouth_funnelD": 0.6, "CTRL_R_mouth_funnelD": 0.6,
        "CTRL_L_mouth_purseU": 0.2, "CTRL_R_mouth_purseU": 0.2,
        "CTRL_L_mouth_purseD": 0.2, "CTRL_R_mouth_purseD": 0.2,
    }),
    (140, "ou", {
        "CTRL_C_jaw.Y": -0.15,
        "CTRL_L_mouth_funnelU": 0.5, "CTRL_R_mouth_funnelU": 0.5,
        "CTRL_L_mouth_funnelD": 0.5, "CTRL_R_mouth_funnelD": 0.5,
        "CTRL_L_mouth_purseU": 0.7, "CTRL_R_mouth_purseU": 0.7,
        "CTRL_L_mouth_purseD": 0.7, "CTRL_R_mouth_purseD": 0.7,
        "CTRL_L_mouth_tightenU": 0.5, "CTRL_R_mouth_tightenU": 0.5,
        "CTRL_L_mouth_tightenD": 0.5, "CTRL_R_mouth_tightenD": 0.5,
    }),
]

# Build channel lookup: control_base_name -> channel object
# Channel names are like "CTRL_L_mouth_pressU_59" - we match by prefix before the trailing _NN suffix
channel_map = {}
face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            for ch in face_section.get_all_channels():
                ch_name = ch.get_name()
                # Strip trailing _NN suffix to get base control name
                # e.g., "CTRL_L_mouth_pressU_59" -> "CTRL_L_mouth_pressU"
                # But vec2d channels are like "CTRL_C_jaw.X_66" -> "CTRL_C_jaw.X"
                parts = ch_name.rsplit('_', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    base_name = parts[0]
                else:
                    base_name = ch_name
                channel_map[base_name] = ch
            break

out.append(f"Built channel map: {len(channel_map)} channels")

# Collect all control names used across all visemes
all_ctrls = set()
for frame, name, controls in visemes:
    for ctrl in controls:
        all_ctrls.add(ctrl)

out.append(f"Total unique controls: {len(all_ctrls)}")

# Check which controls map to channels
missing = []
for ctrl in sorted(all_ctrls):
    if ctrl not in channel_map:
        missing.append(ctrl)
if missing:
    out.append(f"Controls without channels: {missing}")

errors = []

# Key each viseme
out.append("\nKeying visemes (direct channel)...")
for frame, name, controls in visemes:
    keyed = 0
    # Key explicit values for this viseme
    for ctrl, val in controls.items():
        if ctrl in channel_map:
            ch = channel_map[ctrl]
            try:
                ch.add_key(unreal.FrameNumber(frame * TICKS), float(val))
                keyed += 1
            except Exception as e:
                errors.append(f"{ctrl}@{frame}: {e}")
        else:
            errors.append(f"{ctrl}@{frame}: channel not found")

    # Key zero for controls NOT used by this viseme (prevents pre-extrapolation)
    for ctrl in all_ctrls:
        if ctrl not in controls and ctrl in channel_map:
            try:
                channel_map[ctrl].add_key(unreal.FrameNumber(frame * TICKS), 0.0)
            except Exception as e:
                errors.append(f"zero {ctrl}@{frame}: {e}")

    out.append(f"  Frame {frame:3d}: {name} ({keyed} controls)")

# Verify total keys
total_keys = 0
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                total_keys += len(list(ch.get_keys()))
            break

out.append(f"\nTotal keys created: {total_keys}")

if errors:
    unique = list(set(errors))
    out.append(f"\n{len(unique)} errors:")
    for e in unique[:20]:
        out.append(f"  {e}")
else:
    out.append("All visemes keyed successfully!")

# Scrub to TH for visual check
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30)
out.append("Scrubbed to frame 30 (TH)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
