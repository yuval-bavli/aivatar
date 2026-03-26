"""
Re-register scalar parameters in the face section, then key all visemes.
The parameter removal nuked the registrations that set_local_control_rig_float needs.
"""
import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

rigs = lib.get_control_rigs(level_seq)
face_rig = None
for proxy in rigs:
    cr = proxy.control_rig
    if "Face" in cr.get_name():
        face_rig = cr
        break

# Get face section
face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            break

# List all float control names we need
float_controls = [
    "CTRL_L_mouth_pressU", "CTRL_R_mouth_pressU",
    "CTRL_L_mouth_pressD", "CTRL_R_mouth_pressD",
    "CTRL_L_mouth_tightenU", "CTRL_R_mouth_tightenU",
    "CTRL_L_mouth_tightenD", "CTRL_R_mouth_tightenD",
    "CTRL_L_mouth_lipsRollD", "CTRL_R_mouth_lipsRollD",
    "CTRL_L_mouth_lipBiteU", "CTRL_R_mouth_lipBiteU",
    "CTRL_L_mouth_upperLipRaise", "CTRL_R_mouth_upperLipRaise",
    "CTRL_C_tongue_inOut", "CTRL_C_tongue_press",
    "CTRL_C_jaw_openExtreme",
    "CTRL_L_mouth_funnelU", "CTRL_R_mouth_funnelU",
    "CTRL_L_mouth_funnelD", "CTRL_R_mouth_funnelD",
    "CTRL_L_mouth_purseU", "CTRL_R_mouth_purseU",
    "CTRL_L_mouth_purseD", "CTRL_R_mouth_purseD",
    "CTRL_L_mouth_stretch", "CTRL_R_mouth_stretch",
    "CTRL_L_mouth_cornerPull", "CTRL_R_mouth_cornerPull",
]

# Re-register scalar parameters
registered = 0
for ctrl in float_controls:
    try:
        face_section.add_scalar_parameter(ctrl, 0.0)
        registered += 1
    except Exception as e:
        out.append(f"Failed to register {ctrl}: {e}")

out.append(f"Registered {registered} scalar parameters")

# Check total channels now
channels = face_section.get_all_channels()
out.append(f"Total channels: {len(channels)}")

# Now clear any keys and re-key
for ch in channels:
    keys = list(ch.get_keys())
    if keys:
        for k in reversed(keys):
            ch.remove_key(k)

TICKS = 800
TR = unreal.MovieSceneTimeUnit.TICK_RESOLUTION
errors = []

def sf(name, frame, val):
    try:
        lib.set_local_control_rig_float(level_seq, face_rig, name,
            unreal.FrameNumber(frame * TICKS), float(val), time_unit=TR, set_key=True)
    except Exception as e:
        errors.append(f"{name}@{frame}: {e}")

def sv2(name, frame, x, y):
    try:
        lib.set_local_control_rig_vector2d(level_seq, face_rig, name,
            unreal.FrameNumber(frame * TICKS), unreal.Vector2D(float(x), float(y)),
            time_unit=TR, set_key=True)
    except Exception as e:
        errors.append(f"{name}@{frame}: {e}")

visemes = [
    (0, "sil", {"CTRL_C_jaw": (0, 0)}),
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
        "CTRL_C_jaw": (0, -0.5),
        "CTRL_C_tongue_inOut": 0.9,
        "CTRL_C_tongue_tipMove": (0, 0.4),
    }),
    (40, "DD", {
        "CTRL_C_jaw": (0, -0.35),
        "CTRL_C_tongue_press": 0.5,
    }),
    (50, "kk", {"CTRL_C_jaw": (0, -0.3)}),
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

out.append("\nKeying visemes...")
for frame, name, controls in visemes:
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)
    for ctrl, val in controls.items():
        if isinstance(val, tuple):
            sv2(ctrl, frame, val[0], val[1])
        else:
            sf(ctrl, frame, val)
    out.append(f"  Frame {frame:3d}: {name}")

if errors:
    out.append(f"\n{len(set(errors))} errors:")
    for e in list(set(errors))[:20]:
        out.append(f"  {e}")
else:
    out.append("\nAll keyed successfully!")

# Final check
keyed_channels = 0
for ch in face_section.get_all_channels():
    if list(ch.get_keys()):
        keyed_channels += 1
out.append(f"\nChannels with keys: {keyed_channels}")
out.append(f"Total channels: {len(face_section.get_all_channels())}")

# Scrub to PP for user to verify
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(10 * TICKS)
out.append("Scrubbed to frame 10 (PP)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
