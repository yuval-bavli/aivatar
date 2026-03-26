"""
Key 15 Azure viseme poses using add_scalar_parameter_key / add_vector2d_parameter_key.
These APIs use DISPLAY RATE frame numbers (not ticks).
"""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

if not level_seq:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: No level sequence open")
    raise SystemExit

# Find the Face_ControlBoard section
face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            break

if not face_section:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: Face section not found")
    raise SystemExit

out.append("Found Face_ControlBoard section")

# Viseme data: frame -> (name, {control: value})
# scalar controls use float values
# vec2d controls use (x, y) tuples
visemes = [
    (0, "sil", {
        "CTRL_C_jaw": (0, 0),
    }),
    (10, "PP", {
        "CTRL_C_jaw": (0, -0.05),
        "CTRL_L_mouth_pressU": 0.8, "CTRL_R_mouth_pressU": 0.8,
        "CTRL_L_mouth_pressD": 0.8, "CTRL_R_mouth_pressD": 0.8,
        "CTRL_L_mouth_tightenU": 0.5, "CTRL_R_mouth_tightenU": 0.5,
        "CTRL_L_mouth_tightenD": 0.5, "CTRL_R_mouth_tightenD": 0.5,
    }),
    (20, "FF", {
        "CTRL_C_jaw": (0, -0.15),
        "CTRL_L_mouth_lipsRollD": 0.7, "CTRL_R_mouth_lipsRollD": 0.7,
        "CTRL_L_mouth_lipBiteU": 0.6, "CTRL_R_mouth_lipBiteU": 0.6,
        "CTRL_L_mouth_upperLipRaise": 0.2, "CTRL_R_mouth_upperLipRaise": 0.2,
    }),
    (30, "TH", {
        "CTRL_C_jaw": (0, -1.0),
        "CTRL_C_jaw_openExtreme": 1.0,
        "CTRL_C_tongue_inOut": 0.9,
        "CTRL_C_tongue_tipMove": (0, 0.4),
        "CTRL_L_mouth_upperLipRaise": 0.3, "CTRL_R_mouth_upperLipRaise": 0.3,
        "CTRL_L_mouth_lowerLipDepress": 0.3, "CTRL_R_mouth_lowerLipDepress": 0.3,
    }),
    (40, "DD", {
        "CTRL_C_jaw": (0, -0.35),
        "CTRL_C_tongue_press": 0.5,
    }),
    (50, "kk", {
        "CTRL_C_jaw": (0, -0.3),
    }),
    (60, "CH", {
        "CTRL_C_jaw": (0, -0.15),
        "CTRL_L_mouth_funnelU": 0.6, "CTRL_R_mouth_funnelU": 0.6,
        "CTRL_L_mouth_funnelD": 0.6, "CTRL_R_mouth_funnelD": 0.6,
        "CTRL_L_mouth_purseU": 0.3, "CTRL_R_mouth_purseU": 0.3,
        "CTRL_L_mouth_purseD": 0.3, "CTRL_R_mouth_purseD": 0.3,
        "CTRL_L_mouth_tightenU": 0.3, "CTRL_R_mouth_tightenU": 0.3,
        "CTRL_L_mouth_tightenD": 0.3, "CTRL_R_mouth_tightenD": 0.3,
    }),
    (70, "SS", {
        "CTRL_C_jaw": (0, -0.08),
        "CTRL_L_mouth_stretch": 0.5, "CTRL_R_mouth_stretch": 0.5,
    }),
    (80, "nn", {
        "CTRL_C_jaw": (0, -0.15),
        "CTRL_C_tongue_press": 0.4,
    }),
    (90, "RR", {
        "CTRL_C_jaw": (0, -0.2),
        "CTRL_L_mouth_funnelU": 0.3, "CTRL_R_mouth_funnelU": 0.3,
        "CTRL_L_mouth_funnelD": 0.3, "CTRL_R_mouth_funnelD": 0.3,
    }),
    (100, "aa", {
        "CTRL_C_jaw": (0, -0.8),
        "CTRL_C_jaw_openExtreme": 0.3,
    }),
    (110, "E", {
        "CTRL_C_jaw": (0, -0.4),
        "CTRL_L_mouth_stretch": 0.4, "CTRL_R_mouth_stretch": 0.4,
        "CTRL_L_mouth_cornerPull": 0.15, "CTRL_R_mouth_cornerPull": 0.15,
    }),
    (120, "ih", {
        "CTRL_C_jaw": (0, -0.15),
        "CTRL_L_mouth_stretch": 0.6, "CTRL_R_mouth_stretch": 0.6,
        "CTRL_L_mouth_cornerPull": 0.3, "CTRL_R_mouth_cornerPull": 0.3,
    }),
    (130, "oh", {
        "CTRL_C_jaw": (0, -0.4),
        "CTRL_L_mouth_funnelU": 0.6, "CTRL_R_mouth_funnelU": 0.6,
        "CTRL_L_mouth_funnelD": 0.6, "CTRL_R_mouth_funnelD": 0.6,
        "CTRL_L_mouth_purseU": 0.2, "CTRL_R_mouth_purseU": 0.2,
        "CTRL_L_mouth_purseD": 0.2, "CTRL_R_mouth_purseD": 0.2,
    }),
    (140, "ou", {
        "CTRL_C_jaw": (0, -0.15),
        "CTRL_L_mouth_funnelU": 0.5, "CTRL_R_mouth_funnelU": 0.5,
        "CTRL_L_mouth_funnelD": 0.5, "CTRL_R_mouth_funnelD": 0.5,
        "CTRL_L_mouth_purseU": 0.7, "CTRL_R_mouth_purseU": 0.7,
        "CTRL_L_mouth_purseD": 0.7, "CTRL_R_mouth_purseD": 0.7,
        "CTRL_L_mouth_tightenU": 0.5, "CTRL_R_mouth_tightenU": 0.5,
        "CTRL_L_mouth_tightenD": 0.5, "CTRL_R_mouth_tightenD": 0.5,
    }),
]

# Collect all control names by type
all_scalar_ctrls = set()
all_vec2d_ctrls = set()
for frame, name, controls in visemes:
    for ctrl, val in controls.items():
        if isinstance(val, tuple):
            all_vec2d_ctrls.add(ctrl)
        else:
            all_scalar_ctrls.add(ctrl)

out.append(f"Scalar controls: {len(all_scalar_ctrls)}, Vec2D controls: {len(all_vec2d_ctrls)}")

TICKS = 800
errors = []
out.append("\nKeying visemes...")
for frame, name, controls in visemes:
    keyed = 0
    tick = frame * TICKS
    # Key explicit values
    for ctrl, val in controls.items():
        try:
            if isinstance(val, tuple):
                face_section.add_vector2d_parameter_key(
                    ctrl, unreal.FrameNumber(tick), unreal.Vector2D(float(val[0]), float(val[1])))
            else:
                face_section.add_scalar_parameter_key(
                    ctrl, unreal.FrameNumber(tick), float(val))
            keyed += 1
        except Exception as e:
            errors.append(f"{ctrl}@{frame}: {e}")

    # Key zeros for unused scalar controls
    for ctrl in all_scalar_ctrls:
        if ctrl not in controls:
            try:
                face_section.add_scalar_parameter_key(
                    ctrl, unreal.FrameNumber(tick), 0.0)
            except Exception as e:
                errors.append(f"zero {ctrl}@{frame}: {e}")

    # Key zeros for unused vec2d controls
    for ctrl in all_vec2d_ctrls:
        if ctrl not in controls:
            try:
                face_section.add_vector2d_parameter_key(
                    ctrl, unreal.FrameNumber(tick), unreal.Vector2D(0, 0))
            except Exception as e:
                errors.append(f"zero {ctrl}@{frame}: {e}")

    out.append(f"  Frame {frame:3d}: {name} ({keyed} controls)")

# Verify
total_keys = 0
for ch in face_section.get_all_channels():
    total_keys += len(list(ch.get_keys()))
out.append(f"\nTotal keys: {total_keys}")

if errors:
    unique = list(set(errors))
    out.append(f"\n{len(unique)} errors:")
    for e in unique[:20]:
        out.append(f"  {e}")
else:
    out.append("All visemes keyed successfully!")

# Scrub to TH
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30)
out.append("Scrubbed to frame 30 (TH)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
