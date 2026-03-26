"""
Key all 15 Azure viseme poses using ControlRigSequencerLibrary.
This is the correct API that actually drives the MetaHuman face rig.

Visemes keyed every 10 frames (at 30fps = ~0.33s each):
  Frame 0=sil, 10=PP, 20=FF, 30=TH, 40=DD, 50=kk, 60=CH, 70=SS,
  80=nn, 90=RR, 100=aa, 110=E, 120=ih, 130=oh, 140=ou
"""
import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

if not level_seq:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: No level sequence open")
    raise SystemExit

# Get face control rig
rigs = lib.get_control_rigs(level_seq)
face_rig = None
for proxy in rigs:
    cr = proxy.control_rig
    if "Face" in cr.get_name():
        face_rig = cr
        break

if not face_rig:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: Face control rig not found")
    raise SystemExit

out.append(f"Face rig: {face_rig.get_name()}")

# Clear existing keys first by setting all controls to 0 at all viseme frames
# Then set the actual values

DT = unreal.MovieSceneTimeUnit.DISPLAY_RATE
errors = []

def set_float(name, frame, value):
    try:
        fn = unreal.FrameNumber(frame)
        lib.set_local_control_rig_float(level_seq, face_rig, name, fn, float(value),
            time_unit=DT, set_key=True)
    except Exception as e:
        errors.append(f"{name}@{frame}: {e}")

def set_vec2d(name, frame, x, y):
    try:
        fn = unreal.FrameNumber(frame)
        vec = unreal.Vector2D(float(x), float(y))
        lib.set_local_control_rig_vector2d(level_seq, face_rig, name, fn, vec,
            time_unit=DT, set_key=True)
    except Exception as e:
        errors.append(f"{name}@{frame}: {e}")

# All mouth-related controls that we zero out
MOUTH_SCALARS = [
    "mouth_cornerPull", "mouth_cornerDepress", "mouth_stretch",
    "mouth_funnelU", "mouth_funnelD", "mouth_purseU", "mouth_purseD",
    "mouth_upperLipRaise", "mouth_lowerLipDepress",
    "mouth_lipsRollU", "mouth_lipsRollD",
    "mouth_pressU", "mouth_pressD",
    "mouth_tightenU", "mouth_tightenD",
    "mouth_lipsBlow", "mouth_lipsPressU", "mouth_lipsPressD",
    "mouth_stretchLipsClose", "mouth_sharpCornerPull",
    "mouth_pushPullU", "mouth_pushPullD",
    "mouth_lipBiteU", "mouth_lipBiteD",
]

def key_all_zero(frame):
    """Reset all mouth controls to zero at a frame."""
    set_vec2d("CTRL_C_jaw", frame, 0, 0)
    set_float("CTRL_C_jaw_fwdBack", frame, 0)
    set_float("CTRL_C_jaw_openExtreme", frame, 0)
    set_vec2d("CTRL_C_mouth", frame, 0, 0)
    for side in ["CTRL_L_", "CTRL_R_"]:
        for ctrl in MOUTH_SCALARS:
            set_float(side + ctrl, frame, 0)
    set_float("CTRL_C_tongue_inOut", frame, 0)
    set_float("CTRL_C_tongue_press", frame, 0)
    set_vec2d("CTRL_C_tongue_tipMove", frame, 0, 0)
    set_float("CTRL_C_tongue_thickThin", frame, 0)

# Viseme definitions
VISEMES = [
    (0,   "sil", "Silent/rest"),
    (10,  "PP",  "Lips pressed"),
    (20,  "FF",  "Lower lip under teeth"),
    (30,  "TH",  "Tongue between teeth"),
    (40,  "DD",  "Tongue behind teeth"),
    (50,  "kk",  "Back tongue"),
    (60,  "CH",  "Rounded lips"),
    (70,  "SS",  "Teeth together spread"),
    (80,  "nn",  "Tongue up relaxed"),
    (90,  "RR",  "Slightly rounded"),
    (100, "aa",  "Wide open"),
    (110, "E",   "Mid open spread"),
    (120, "ih",  "Narrow spread"),
    (130, "oh",  "Round open"),
    (140, "ou",  "Tight pucker"),
]

out.append("Keying visemes...")

for frame, name, desc in VISEMES:
    key_all_zero(frame)

    if name == "sil":
        pass  # all zero

    elif name == "PP":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.05)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_pressU", frame, 0.8)
            set_float(s + "mouth_pressD", frame, 0.8)
            set_float(s + "mouth_tightenU", frame, 0.5)
            set_float(s + "mouth_tightenD", frame, 0.5)

    elif name == "FF":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.15)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_lipsRollD", frame, 0.7)
            set_float(s + "mouth_lipBiteU", frame, 0.6)
            set_float(s + "mouth_upperLipRaise", frame, 0.2)

    elif name == "TH":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.35)
        set_float("CTRL_C_tongue_inOut", frame, 0.8)
        set_vec2d("CTRL_C_tongue_tipMove", frame, 0, 0.4)
        set_float("CTRL_C_tongue_thickThin", frame, -0.3)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_lowerLipDepress", frame, 0.35)
            set_float(s + "mouth_upperLipRaise", frame, 0.25)

    elif name == "DD":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.35)
        set_float("CTRL_C_tongue_press", frame, 0.5)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_lowerLipDepress", frame, 0.3)
            set_float(s + "mouth_upperLipRaise", frame, 0.15)

    elif name == "kk":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.3)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_lowerLipDepress", frame, 0.25)

    elif name == "CH":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.15)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_funnelU", frame, 0.6)
            set_float(s + "mouth_funnelD", frame, 0.6)
            set_float(s + "mouth_purseU", frame, 0.3)
            set_float(s + "mouth_purseD", frame, 0.3)
            set_float(s + "mouth_tightenU", frame, 0.3)
            set_float(s + "mouth_tightenD", frame, 0.3)

    elif name == "SS":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.08)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_stretch", frame, 0.6)
            set_float(s + "mouth_stretchLipsClose", frame, 0.4)
            set_float(s + "mouth_lowerLipDepress", frame, 0.1)

    elif name == "nn":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.15)
        set_float("CTRL_C_tongue_press", frame, 0.4)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_lowerLipDepress", frame, 0.15)

    elif name == "RR":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.2)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_funnelU", frame, 0.35)
            set_float(s + "mouth_funnelD", frame, 0.35)
            set_float(s + "mouth_purseU", frame, 0.15)
            set_float(s + "mouth_purseD", frame, 0.15)
            set_float(s + "mouth_lowerLipDepress", frame, 0.15)

    elif name == "aa":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.7)
        set_float("CTRL_C_jaw_openExtreme", frame, 0.3)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_lowerLipDepress", frame, 0.6)
            set_float(s + "mouth_upperLipRaise", frame, 0.4)
            set_float(s + "mouth_stretch", frame, 0.3)
            set_float(s + "mouth_cornerDepress", frame, 0.2)

    elif name == "E":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.4)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_stretch", frame, 0.45)
            set_float(s + "mouth_lowerLipDepress", frame, 0.35)
            set_float(s + "mouth_upperLipRaise", frame, 0.2)
            set_float(s + "mouth_cornerPull", frame, 0.15)

    elif name == "ih":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.15)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_stretch", frame, 0.7)
            set_float(s + "mouth_cornerPull", frame, 0.35)
            set_float(s + "mouth_lowerLipDepress", frame, 0.15)
            set_float(s + "mouth_upperLipRaise", frame, 0.1)

    elif name == "oh":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.4)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_funnelU", frame, 0.7)
            set_float(s + "mouth_funnelD", frame, 0.7)
            set_float(s + "mouth_purseU", frame, 0.2)
            set_float(s + "mouth_purseD", frame, 0.2)
            set_float(s + "mouth_lowerLipDepress", frame, 0.3)
            set_float(s + "mouth_upperLipRaise", frame, 0.2)
            set_float(s + "mouth_tightenU", frame, 0.3)
            set_float(s + "mouth_tightenD", frame, 0.3)

    elif name == "ou":
        set_vec2d("CTRL_C_jaw", frame, 0, -0.15)
        for s in ["CTRL_L_", "CTRL_R_"]:
            set_float(s + "mouth_funnelU", frame, 0.5)
            set_float(s + "mouth_funnelD", frame, 0.5)
            set_float(s + "mouth_purseU", frame, 0.7)
            set_float(s + "mouth_purseD", frame, 0.7)
            set_float(s + "mouth_tightenU", frame, 0.5)
            set_float(s + "mouth_tightenD", frame, 0.5)

    out.append(f"  Frame {frame:3d}: {name:3s} - {desc} OK")

# Report errors
if errors:
    unique = list(set(errors))
    out.append(f"\n{len(unique)} unique errors:")
    for e in unique[:20]:
        out.append(f"  {e}")
else:
    out.append("\nAll 15 visemes keyed successfully!")

# Scrub to aa for verification
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(100 * 800)
out.append("Scrubbed to frame 100 (aa)")

out.append("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
