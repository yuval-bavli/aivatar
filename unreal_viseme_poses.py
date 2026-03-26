"""
MetaHuman Viseme Keyframer — keys 15 Azure viseme poses on Face_ControlBoard_CtrlRig

Run:  exec(open("c:/Users/yuval/src/aivatar/unreal_viseme_poses.py").read())

Visemes are keyed every 10 frames (at 30fps = ~0.33s each):
  Frame 0=sil, 10=PP, 20=FF, 30=TH, 40=DD, 50=kk, 60=CH, 70=SS,
  80=nn, 90=RR, 100=aa, 110=E, 120=ih, 130=oh, 140=ou
"""
import unreal

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
if not level_seq:
    print("ERROR: No Level Sequence open"); raise SystemExit

face_section = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "ControlBoard" in str(track.get_display_name()):
            sections = track.get_sections()
            if sections:
                face_section = sections[0]

if not face_section:
    print("ERROR: Face_ControlBoard_CtrlRig section not found"); raise SystemExit

# Tick resolution: 800 ticks per frame at 30fps
TICKS_PER_FRAME = 800

# First, clear existing keys by removing and re-adding section
# (or we just overwrite — keys at same tick overwrite)

# ============================================================
# Helper functions
# ============================================================
def key_scalar(name, frame, value):
    """Key a scalar parameter at given frame (in display frames, not ticks)."""
    fn = unreal.FrameNumber(frame * TICKS_PER_FRAME)
    face_section.add_scalar_parameter_key(name, fn, float(value))

def key_vector2d(name, frame, x, y):
    """Key a 2D parameter at given frame (in display frames, not ticks)."""
    fn = unreal.FrameNumber(frame * TICKS_PER_FRAME)
    vec = unreal.Vector2D(x, y)
    face_section.add_vector2d_parameter_key(name, fn, vec)

# ============================================================
# Viseme definitions
# ============================================================
# Key controls used:
#   CTRL_C_jaw (2D: X=left/right, Y=open — negative Y = jaw down/open)
#   CTRL_C_jaw_fwdBack (scalar: positive = forward)
#   CTRL_L/R_mouth_cornerPull (scalar: smile/pull corners up)
#   CTRL_L/R_mouth_cornerDepress (scalar: frown/pull corners down)
#   CTRL_L/R_mouth_stretch (scalar: widen mouth)
#   CTRL_L/R_mouth_funnelU/D (scalar: funnel/round lips)
#   CTRL_L/R_mouth_purseU/D (scalar: pucker/purse lips)
#   CTRL_L/R_mouth_upperLipRaise (scalar: raise upper lip)
#   CTRL_L/R_mouth_lowerLipDepress (scalar: lower the lower lip)
#   CTRL_L/R_mouth_lipsRollU/D (scalar: roll lips inward)
#   CTRL_L/R_mouth_pressU/D (scalar: press lips together)
#   CTRL_L/R_mouth_tightenU/D (scalar: tighten lips)
#   CTRL_C_mouth (2D: overall mouth position)
#   CTRL_C_tongue_inOut (scalar: tongue protrusion)

VISEMES = [
    # (frame, name, description)
    (0,   "sil", "Silent/rest"),
    (10,  "PP",  "Lips pressed — Papa"),
    (20,  "FF",  "Lower lip under teeth — Fish"),
    (30,  "TH",  "Tongue between teeth — Think"),
    (40,  "DD",  "Tongue behind teeth — Day"),
    (50,  "kk",  "Back tongue — King"),
    (60,  "CH",  "Rounded lips — Shoe"),
    (70,  "SS",  "Teeth together spread — See"),
    (80,  "nn",  "Tongue up relaxed — No"),
    (90,  "RR",  "Slightly rounded — Red"),
    (100, "aa",  "Wide open — fAther"),
    (110, "E",   "Mid open spread — bEd"),
    (120, "ih",  "Narrow spread — bEAt"),
    (130, "oh",  "Round open — bOAt"),
    (140, "ou",  "Tight pucker — bOOt"),
]

def key_all_zero(frame):
    """Reset all mouth controls to zero at a frame."""
    key_vector2d("CTRL_C_jaw", frame, 0, 0)
    key_scalar("CTRL_C_jaw_fwdBack", frame, 0)
    key_scalar("CTRL_C_jaw_openExtreme", frame, 0)
    key_vector2d("CTRL_C_mouth", frame, 0, 0)
    for side in ["CTRL_L_", "CTRL_R_"]:
        key_scalar(side + "mouth_cornerPull", frame, 0)
        key_scalar(side + "mouth_cornerDepress", frame, 0)
        key_scalar(side + "mouth_stretch", frame, 0)
        key_scalar(side + "mouth_funnelU", frame, 0)
        key_scalar(side + "mouth_funnelD", frame, 0)
        key_scalar(side + "mouth_purseU", frame, 0)
        key_scalar(side + "mouth_purseD", frame, 0)
        key_scalar(side + "mouth_upperLipRaise", frame, 0)
        key_scalar(side + "mouth_lowerLipDepress", frame, 0)
        key_scalar(side + "mouth_lipsRollU", frame, 0)
        key_scalar(side + "mouth_lipsRollD", frame, 0)
        key_scalar(side + "mouth_pressU", frame, 0)
        key_scalar(side + "mouth_pressD", frame, 0)
        key_scalar(side + "mouth_tightenU", frame, 0)
        key_scalar(side + "mouth_tightenD", frame, 0)
        key_scalar(side + "mouth_lipsBlow", frame, 0)
        key_scalar(side + "mouth_lipsPressU", frame, 0)
        key_scalar(side + "mouth_lipsPressD", frame, 0)
        key_scalar(side + "mouth_stretchLipsClose", frame, 0)
        key_scalar(side + "mouth_sharpCornerPull", frame, 0)
        key_scalar(side + "mouth_pushPullU", frame, 0)
        key_scalar(side + "mouth_pushPullD", frame, 0)
    key_scalar("CTRL_C_tongue_inOut", frame, 0)
    key_scalar("CTRL_C_tongue_press", frame, 0)

# ============================================================
# Key each viseme
# ============================================================
errors = []

for frame, name, desc in VISEMES:
    try:
        # Start with everything zeroed
        key_all_zero(frame)

        if name == "sil":
            pass  # all zero = rest

        elif name == "PP":
            # Lips pressed firmly together
            key_vector2d("CTRL_C_jaw", frame, 0, -0.05)  # barely open
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_pressU", frame, 0.8)
                key_scalar(s + "mouth_pressD", frame, 0.8)
                key_scalar(s + "mouth_tightenU", frame, 0.5)
                key_scalar(s + "mouth_tightenD", frame, 0.5)

        elif name == "FF":
            # Lower lip tucked under upper teeth
            key_vector2d("CTRL_C_jaw", frame, 0, -0.15)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lipsRollD", frame, 0.7)  # roll lower lip in
                key_scalar(s + "mouth_lipBiteU", frame, 0.6)   # bite upper teeth on lower lip
                key_scalar(s + "mouth_upperLipRaise", frame, 0.2)

        elif name == "TH":
            # Tongue between teeth, mouth slightly open
            key_vector2d("CTRL_C_jaw", frame, 0, -0.25)
            key_scalar("CTRL_C_tongue_inOut", frame, 0.4)  # tongue slightly out
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.3)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.2)

        elif name == "DD":
            # Tongue behind upper teeth, mouth moderately open
            key_vector2d("CTRL_C_jaw", frame, 0, -0.35)
            key_scalar("CTRL_C_tongue_press", frame, 0.5)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.3)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.15)

        elif name == "kk":
            # Back tongue raised, mouth moderately open
            key_vector2d("CTRL_C_jaw", frame, 0, -0.3)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.25)

        elif name == "CH":
            # Lips rounded forward, slight opening (sh/ch)
            key_vector2d("CTRL_C_jaw", frame, 0, -0.15)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_funnelU", frame, 0.6)
                key_scalar(s + "mouth_funnelD", frame, 0.6)
                key_scalar(s + "mouth_purseU", frame, 0.3)
                key_scalar(s + "mouth_purseD", frame, 0.3)
                key_scalar(s + "mouth_tightenU", frame, 0.3)
                key_scalar(s + "mouth_tightenD", frame, 0.3)

        elif name == "SS":
            # Teeth almost together, lips spread wide
            key_vector2d("CTRL_C_jaw", frame, 0, -0.08)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_stretch", frame, 0.6)
                key_scalar(s + "mouth_stretchLipsClose", frame, 0.4)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.1)

        elif name == "nn":
            # Tongue tip up, slightly open, relaxed
            key_vector2d("CTRL_C_jaw", frame, 0, -0.15)
            key_scalar("CTRL_C_tongue_press", frame, 0.4)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.15)

        elif name == "RR":
            # Lips slightly rounded and forward
            key_vector2d("CTRL_C_jaw", frame, 0, -0.2)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_funnelU", frame, 0.35)
                key_scalar(s + "mouth_funnelD", frame, 0.35)
                key_scalar(s + "mouth_purseU", frame, 0.15)
                key_scalar(s + "mouth_purseD", frame, 0.15)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.15)

        elif name == "aa":
            # Wide open mouth — most dramatic
            key_vector2d("CTRL_C_jaw", frame, 0, -0.7)
            key_scalar("CTRL_C_jaw_openExtreme", frame, 0.3)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.6)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.4)
                key_scalar(s + "mouth_stretch", frame, 0.3)
                key_scalar(s + "mouth_cornerDepress", frame, 0.2)

        elif name == "E":
            # Mid open, lips spread — "eh"
            key_vector2d("CTRL_C_jaw", frame, 0, -0.4)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_stretch", frame, 0.45)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.35)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.2)
                key_scalar(s + "mouth_cornerPull", frame, 0.15)

        elif name == "ih":
            # Narrow opening, lips spread wide — "ee"
            key_vector2d("CTRL_C_jaw", frame, 0, -0.15)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_stretch", frame, 0.7)
                key_scalar(s + "mouth_cornerPull", frame, 0.35)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.15)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.1)

        elif name == "oh":
            # Round open "O" — lips forward, round opening
            key_vector2d("CTRL_C_jaw", frame, 0, -0.4)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_funnelU", frame, 0.7)
                key_scalar(s + "mouth_funnelD", frame, 0.7)
                key_scalar(s + "mouth_purseU", frame, 0.2)
                key_scalar(s + "mouth_purseD", frame, 0.2)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.3)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.2)
                key_scalar(s + "mouth_tightenU", frame, 0.3)
                key_scalar(s + "mouth_tightenD", frame, 0.3)

        elif name == "ou":
            # Tight pucker forward — "oo"
            key_vector2d("CTRL_C_jaw", frame, 0, -0.15)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_funnelU", frame, 0.5)
                key_scalar(s + "mouth_funnelD", frame, 0.5)
                key_scalar(s + "mouth_purseU", frame, 0.7)
                key_scalar(s + "mouth_purseD", frame, 0.7)
                key_scalar(s + "mouth_tightenU", frame, 0.5)
                key_scalar(s + "mouth_tightenD", frame, 0.5)

        print(f"  Frame {frame:3d}: {name:3s} - {desc} OK")

    except Exception as e:
        errors.append(f"Frame {frame} ({name}): {e}")
        print(f"  Frame {frame:3d}: {name:3s} - ERROR: {e}")

if errors:
    print(f"\n{len(errors)} errors occurred:")
    for e in errors:
        print(f"  {e}")
else:
    print(f"\nAll 15 visemes keyed successfully!")

print("\nNext steps:")
print("1. Scrub through the Sequencer timeline to verify the poses look correct")
print("2. Right-click Face_ControlBoard_CtrlRig > Bake Animation")
print("3. Export: Sequencer hamburger menu > Export to FBX")
print("=== DONE ===")
