"""
Key 15 Azure viseme poses — FINAL working version.
Pattern: scrub to frame, then set_local_control_rig_* with set_key=True.
Uses TICK_RESOLUTION with frame*800 for proper frame alignment.
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

# Clear ALL existing keys
face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            break
if face_section:
    cleared = 0
    for ch in face_section.get_all_channels():
        try:
            keys = list(ch.get_keys())
            if keys:
                for k in reversed(keys):
                    ch.remove_key(k)
                cleared += 1
        except:
            pass
    out.append(f"Cleared {cleared} channels")

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

# Viseme data: frame -> (name, {control: value})
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
        "CTRL_C_jaw": (0, -0.5),
        "CTRL_C_jaw_openExtreme": 1.0,
        "CTRL_C_tongue_inOut": 0.9,
        "CTRL_C_tongue_tipMove": (0, 0.4),
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

out.append("\nKeying visemes (scrub-then-key)...")

# Collect ALL float and vec2d controls used across all visemes
all_float_ctrls = set()
all_vec2d_ctrls = set()
for frame, name, controls in visemes:
    for ctrl, val in controls.items():
        if isinstance(val, tuple):
            all_vec2d_ctrls.add(ctrl)
        else:
            all_float_ctrls.add(ctrl)

# For each viseme frame, key ALL controls (0 for unused ones)
# This prevents pre/post-extrapolation artifacts
for frame, name, controls in visemes:
    # SCRUB to the frame first — critical for proper keying
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)

    # Key explicit values for controls used by this viseme
    for ctrl, val in controls.items():
        if isinstance(val, tuple):
            sv2(ctrl, frame, val[0], val[1])
        else:
            sf(ctrl, frame, val)

    # Key zero for float controls NOT used by this viseme
    for ctrl in all_float_ctrls:
        if ctrl not in controls:
            sf(ctrl, frame, 0.0)

    out.append(f"  Frame {frame:3d}: {name}")

if errors:
    unique = list(set(errors))
    out.append(f"\n{len(unique)} errors:")
    for e in unique[:20]:
        out.append(f"  {e}")
else:
    out.append("\nAll 15 visemes keyed successfully!")

# Scrub to TH for visual check
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30 * TICKS)
out.append("Scrubbed to frame 30 (TH)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
