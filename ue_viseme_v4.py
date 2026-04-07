"""
Key 15 Azure viseme poses — V4 fixed: vec2d patching uses display-rate frames.
"""
import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

if not level_seq:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: No level sequence open")
    raise SystemExit

rigs = lib.get_control_rigs(level_seq)
face_rig = None
for proxy in rigs:
    cr = proxy.control_rig
    if "Face" in cr.get_name():
        face_rig = cr
        break

if not face_rig:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: Face rig not found")
    raise SystemExit

out.append(f"Face rig: {face_rig.get_name()}")

face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            break

if not face_section:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: No face section")
    raise SystemExit

TICKS = 800
TR = unreal.MovieSceneTimeUnit.TICK_RESOLUTION

# Clear ALL existing keys
cleared = 0
for ch in face_section.get_all_channels():
    keys = list(ch.get_keys())
    if keys:
        for k in reversed(keys):
            ch.remove_key(k)
        cleared += 1
out.append(f"Cleared {cleared} channels")

# V4 viseme data
visemes = [
    (0, "sil", {
        "CTRL_C_jaw": (0, 0),
    }),
    (10, "PP", {
        "CTRL_C_jaw": (0, -0.04),
        "CTRL_L_mouth_pressU": 0.8, "CTRL_R_mouth_pressU": 0.8,
        "CTRL_L_mouth_pressD": 0.8, "CTRL_R_mouth_pressD": 0.8,
        "CTRL_L_mouth_tightenU": 0.5, "CTRL_R_mouth_tightenU": 0.5,
        "CTRL_L_mouth_tightenD": 0.5, "CTRL_R_mouth_tightenD": 0.5,
    }),
    (20, "FF", {
        "CTRL_C_jaw": (0, -0.12),
        "CTRL_L_mouth_lipsRollD": 0.7, "CTRL_R_mouth_lipsRollD": 0.7,
        "CTRL_L_mouth_lipBiteU": 0.6, "CTRL_R_mouth_lipBiteU": 0.6,
        "CTRL_L_mouth_upperLipRaise": 0.2, "CTRL_R_mouth_upperLipRaise": 0.2,
    }),
    (30, "TH", {
        "CTRL_C_jaw": (0, -0.55),
        "CTRL_C_tongue_inOut": -0.9,
        "CTRL_C_tongue_tipMove": (0, 0.4),
        "CTRL_L_mouth_upperLipRaise": 0.35, "CTRL_R_mouth_upperLipRaise": 0.35,
        "CTRL_L_mouth_lowerLipDepress": 0.15, "CTRL_R_mouth_lowerLipDepress": 0.15,
        "CTRL_L_mouth_lipsRollD": 0.15, "CTRL_R_mouth_lipsRollD": 0.15,
    }),
    (40, "DD", {
        "CTRL_C_jaw": (0, -0.3),
        "CTRL_C_tongue_press": 0.6,
        "CTRL_C_tongue_inOut": -0.3,
        "CTRL_L_mouth_upperLipRaise": 0.15, "CTRL_R_mouth_upperLipRaise": 0.15,
        "CTRL_L_mouth_lipsRollD": 0.1, "CTRL_R_mouth_lipsRollD": 0.1,
    }),
    (50, "kk", {
        "CTRL_C_jaw": (0, -0.25),
    }),
    (60, "CH", {
        "CTRL_C_jaw": (0, -0.12),
        "CTRL_L_mouth_funnelU": 0.6, "CTRL_R_mouth_funnelU": 0.6,
        "CTRL_L_mouth_funnelD": 0.6, "CTRL_R_mouth_funnelD": 0.6,
        "CTRL_L_mouth_purseU": 0.3, "CTRL_R_mouth_purseU": 0.3,
        "CTRL_L_mouth_purseD": 0.3, "CTRL_R_mouth_purseD": 0.3,
        "CTRL_L_mouth_tightenU": 0.3, "CTRL_R_mouth_tightenU": 0.3,
        "CTRL_L_mouth_tightenD": 0.3, "CTRL_R_mouth_tightenD": 0.3,
    }),
    (70, "SS", {
        "CTRL_C_jaw": (0, -0.06),
        "CTRL_L_mouth_stretch": 0.5, "CTRL_R_mouth_stretch": 0.5,
    }),
    (80, "nn", {
        "CTRL_C_jaw": (0, -0.12),
        "CTRL_C_tongue_press": 0.5,
        "CTRL_C_tongue_inOut": -0.2,
    }),
    (90, "RR", {
        "CTRL_C_jaw": (0, -0.15),
        "CTRL_L_mouth_funnelU": 0.3, "CTRL_R_mouth_funnelU": 0.3,
        "CTRL_L_mouth_funnelD": 0.3, "CTRL_R_mouth_funnelD": 0.3,
        "CTRL_C_tongue_inOut": -0.15,
    }),
    (100, "aa", {
        "CTRL_C_jaw": (0, -0.6),
        "CTRL_L_mouth_upperLipRaise": 0.25, "CTRL_R_mouth_upperLipRaise": 0.25,
        "CTRL_L_mouth_lipsRollD": 0.12, "CTRL_R_mouth_lipsRollD": 0.12,
    }),
    (110, "E", {
        "CTRL_C_jaw": (0, -0.32),
        "CTRL_L_mouth_stretch": 0.4, "CTRL_R_mouth_stretch": 0.4,
        "CTRL_L_mouth_cornerPull": 0.15, "CTRL_R_mouth_cornerPull": 0.15,
        "CTRL_L_mouth_upperLipRaise": 0.15, "CTRL_R_mouth_upperLipRaise": 0.15,
    }),
    (120, "ih", {
        "CTRL_C_jaw": (0, -0.12),
        "CTRL_L_mouth_stretch": 0.6, "CTRL_R_mouth_stretch": 0.6,
        "CTRL_L_mouth_cornerPull": 0.3, "CTRL_R_mouth_cornerPull": 0.3,
    }),
    (130, "oh", {
        "CTRL_C_jaw": (0, -0.35),
        "CTRL_L_mouth_funnelU": 0.6, "CTRL_R_mouth_funnelU": 0.6,
        "CTRL_L_mouth_funnelD": 0.6, "CTRL_R_mouth_funnelD": 0.6,
        "CTRL_L_mouth_purseU": 0.2, "CTRL_R_mouth_purseU": 0.2,
        "CTRL_L_mouth_purseD": 0.2, "CTRL_R_mouth_purseD": 0.2,
    }),
    (140, "ou", {
        "CTRL_C_jaw": (0, -0.12),
        "CTRL_L_mouth_funnelU": 0.5, "CTRL_R_mouth_funnelU": 0.5,
        "CTRL_L_mouth_funnelD": 0.5, "CTRL_R_mouth_funnelD": 0.5,
        "CTRL_L_mouth_purseU": 0.7, "CTRL_R_mouth_purseU": 0.7,
        "CTRL_L_mouth_purseD": 0.7, "CTRL_R_mouth_purseD": 0.7,
        "CTRL_L_mouth_tightenU": 0.5, "CTRL_R_mouth_tightenU": 0.5,
        "CTRL_L_mouth_tightenD": 0.5, "CTRL_R_mouth_tightenD": 0.5,
    }),
]

# Collect all controls by type
all_scalar_ctrls = set()
all_vec2d_ctrls = set()
for frame, name, controls in visemes:
    for ctrl, val in controls.items():
        if isinstance(val, tuple):
            all_vec2d_ctrls.add(ctrl)
        else:
            all_scalar_ctrls.add(ctrl)

out.append(f"Controls: {len(all_scalar_ctrls)} scalar, {len(all_vec2d_ctrls)} vec2d")

# Store desired vec2d values for patching: key=(ctrl_name, display_frame) -> (x, y)
vec2d_targets = {}

errors = []
out.append("\nKeying visemes...")

for frame, name, controls in visemes:
    keyed_scalar = 0
    keyed_vec2d = 0
    frame_ticks = frame * TICKS

    # MUST scrub first
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame_ticks)

    # Key scalar controls
    for ctrl, val in controls.items():
        if not isinstance(val, tuple):
            try:
                lib.set_local_control_rig_float(level_seq, face_rig, ctrl,
                    unreal.FrameNumber(frame_ticks), float(val),
                    time_unit=TR, set_key=True)
                keyed_scalar += 1
            except Exception as e:
                errors.append(f"{ctrl}@{frame}: {e}")

    # Key vec2d controls (API ignores values, writes 0,0 — we patch below)
    for ctrl, val in controls.items():
        if isinstance(val, tuple):
            try:
                lib.set_local_control_rig_vector2d(level_seq, face_rig, ctrl,
                    unreal.FrameNumber(frame_ticks), unreal.Vector2D(float(val[0]), float(val[1])),
                    time_unit=TR, set_key=True)
                vec2d_targets[(ctrl, frame)] = val
                keyed_vec2d += 1
            except Exception as e:
                errors.append(f"v2d {ctrl}@{frame}: {e}")

    # Key zero for unused scalar controls
    for ctrl in all_scalar_ctrls:
        if ctrl not in controls:
            try:
                lib.set_local_control_rig_float(level_seq, face_rig, ctrl,
                    unreal.FrameNumber(frame_ticks), 0.0,
                    time_unit=TR, set_key=True)
            except Exception as e:
                errors.append(f"zero {ctrl}@{frame}: {e}")

    # Key zero for unused vec2d controls
    for ctrl in all_vec2d_ctrls:
        if ctrl not in controls:
            try:
                lib.set_local_control_rig_vector2d(level_seq, face_rig, ctrl,
                    unreal.FrameNumber(frame_ticks), unreal.Vector2D(0, 0),
                    time_unit=TR, set_key=True)
                vec2d_targets[(ctrl, frame)] = (0, 0)
            except Exception as e:
                errors.append(f"zero v2d {ctrl}@{frame}: {e}")

    out.append(f"  Frame {frame:3d}: {name} (scalar={keyed_scalar}, vec2d={keyed_vec2d})")

# FIX: Patch vec2d channel values — compare against DISPLAY-RATE frame, not ticks!
# k.get_time().frame_number.value returns display-rate frames
out.append("\nPatching vec2d values...")
patched = 0
for ch in face_section.get_all_channels():
    ch_name = ch.get_name()
    for (ctrl, display_frame), (xv, yv) in vec2d_targets.items():
        if f"{ctrl}.X" in ch_name:
            for k in ch.get_keys():
                if k.get_time().frame_number.value == display_frame:
                    k.set_value(float(xv))
                    patched += 1
        elif f"{ctrl}.Y" in ch_name:
            for k in ch.get_keys():
                if k.get_time().frame_number.value == display_frame:
                    k.set_value(float(yv))
                    patched += 1
out.append(f"Patched {patched} vec2d key values")

# Verify jaw values by reading back
out.append("\nVerifying jaw.Y keys:")
for ch in face_section.get_all_channels():
    if "CTRL_C_jaw.Y" in ch.get_name():
        for k in ch.get_keys():
            f = k.get_time().frame_number.value
            v = k.get_value()
            out.append(f"  frame {f}: jaw.Y = {v}")
        break

total_keys = 0
keyed_channels = 0
for ch in face_section.get_all_channels():
    n = ch.get_num_keys()
    total_keys += n
    if n > 0:
        keyed_channels += 1
out.append(f"\nTotal: {total_keys} keys in {keyed_channels} channels")

if errors:
    unique = list(set(errors))
    out.append(f"\n{len(unique)} errors:")
    for e in unique[:20]:
        out.append(f"  {e}")
else:
    out.append("All visemes keyed successfully!")

# Scrub to TH for visual check
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30 * TICKS)
out.append("Scrubbed to frame 30 (TH)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
