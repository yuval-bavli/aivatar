"""
Fixed MetaHuman Viseme Keyframer — keys 15 Azure viseme poses on Face_ControlBoard_CtrlRig.

Visemes keyed every 10 frames (at 30fps = ~0.33s each):
  Frame 0=sil, 10=PP, 20=FF, 30=TH, 40=DD, 50=kk, 60=CH, 70=SS,
  80=nn, 90=RR, 100=aa, 110=E, 120=ih, 130=oh, 140=ou
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

# ── 1. Find the level sequence and FACE section specifically ──
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
if not level_seq:
    p("ERROR: No Level Sequence open");
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
    raise SystemExit

p(f"Level Sequence: {level_seq.get_name()}")

face_section = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        tname = str(track.get_display_name())
        if "Face_ControlBoard" in tname:
            sections = track.get_sections()
            if sections:
                face_section = sections[0]
                p(f"Found: {tname}")
                break
    if face_section:
        break

if not face_section:
    p("ERROR: Face_ControlBoard_CtrlRig not found")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
    raise SystemExit

# ── 2. Clear ALL existing keys on ALL channels ──
p("\nClearing existing keys...")
channels = face_section.get_all_channels()
cleared_count = 0
for ch in channels:
    try:
        nkeys = ch.get_num_keys()
        if nkeys > 0:
            # Remove keys from last to first to avoid index shifting
            keys = ch.get_keys()
            for k in reversed(list(keys)):
                ch.remove_key(k)
            cleared_count += 1
    except Exception as e:
        pass
p(f"Cleared keys from {cleared_count} channels")

# ── 3. Set section range: 0 to 150 frames ──
TICKS_PER_FRAME = 800
try:
    face_section.set_start_frame_bounded(True)
    face_section.set_start_frame(0)
    face_section.set_end_frame_bounded(True)
    face_section.set_end_frame(150 * TICKS_PER_FRAME)
    p(f"Section range set: 0 to 150 frames")
except Exception as e:
    p(f"Warning: Could not set section range: {e}")

# ── 4. Key functions ──
errors = []

def key_scalar(name, frame, value):
    """Key a scalar parameter at given frame."""
    fn = unreal.FrameNumber(frame * TICKS_PER_FRAME)
    face_section.add_scalar_parameter_key(name, fn, float(value))

def key_vector2d(name, frame, x, y):
    """Key a 2D parameter at given frame."""
    fn = unreal.FrameNumber(frame * TICKS_PER_FRAME)
    vec = unreal.Vector2D(x, y)
    face_section.add_vector2d_parameter_key(name, fn, vec)

# ── 5. Viseme definitions ──
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
        # Use correct name: lipBiteU exists on the rig
        key_scalar(side + "mouth_lipBiteU", frame, 0)
        key_scalar(side + "mouth_lipBiteD", frame, 0)
    key_scalar("CTRL_C_tongue_inOut", frame, 0)
    key_scalar("CTRL_C_tongue_press", frame, 0)

# ── 6. Key each viseme ──
p("\nKeying visemes...")

for frame, name, desc in VISEMES:
    try:
        key_all_zero(frame)

        if name == "sil":
            pass  # all zero = rest

        elif name == "PP":
            key_vector2d("CTRL_C_jaw", frame, 0, -0.05)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_pressU", frame, 0.8)
                key_scalar(s + "mouth_pressD", frame, 0.8)
                key_scalar(s + "mouth_tightenU", frame, 0.5)
                key_scalar(s + "mouth_tightenD", frame, 0.5)

        elif name == "FF":
            key_vector2d("CTRL_C_jaw", frame, 0, -0.15)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lipsRollD", frame, 0.7)
                key_scalar(s + "mouth_lipBiteU", frame, 0.6)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.2)

        elif name == "TH":
            key_vector2d("CTRL_C_jaw", frame, 0, -0.25)
            key_scalar("CTRL_C_tongue_inOut", frame, 0.4)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.3)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.2)

        elif name == "DD":
            key_vector2d("CTRL_C_jaw", frame, 0, -0.35)
            key_scalar("CTRL_C_tongue_press", frame, 0.5)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.3)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.15)

        elif name == "kk":
            key_vector2d("CTRL_C_jaw", frame, 0, -0.3)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.25)

        elif name == "CH":
            key_vector2d("CTRL_C_jaw", frame, 0, -0.15)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_funnelU", frame, 0.6)
                key_scalar(s + "mouth_funnelD", frame, 0.6)
                key_scalar(s + "mouth_purseU", frame, 0.3)
                key_scalar(s + "mouth_purseD", frame, 0.3)
                key_scalar(s + "mouth_tightenU", frame, 0.3)
                key_scalar(s + "mouth_tightenD", frame, 0.3)

        elif name == "SS":
            key_vector2d("CTRL_C_jaw", frame, 0, -0.08)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_stretch", frame, 0.6)
                key_scalar(s + "mouth_stretchLipsClose", frame, 0.4)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.1)

        elif name == "nn":
            key_vector2d("CTRL_C_jaw", frame, 0, -0.15)
            key_scalar("CTRL_C_tongue_press", frame, 0.4)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.15)

        elif name == "RR":
            key_vector2d("CTRL_C_jaw", frame, 0, -0.2)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_funnelU", frame, 0.35)
                key_scalar(s + "mouth_funnelD", frame, 0.35)
                key_scalar(s + "mouth_purseU", frame, 0.15)
                key_scalar(s + "mouth_purseD", frame, 0.15)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.15)

        elif name == "aa":
            key_vector2d("CTRL_C_jaw", frame, 0, -0.7)
            key_scalar("CTRL_C_jaw_openExtreme", frame, 0.3)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.6)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.4)
                key_scalar(s + "mouth_stretch", frame, 0.3)
                key_scalar(s + "mouth_cornerDepress", frame, 0.2)

        elif name == "E":
            key_vector2d("CTRL_C_jaw", frame, 0, -0.4)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_stretch", frame, 0.45)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.35)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.2)
                key_scalar(s + "mouth_cornerPull", frame, 0.15)

        elif name == "ih":
            key_vector2d("CTRL_C_jaw", frame, 0, -0.15)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_stretch", frame, 0.7)
                key_scalar(s + "mouth_cornerPull", frame, 0.35)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.15)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.1)

        elif name == "oh":
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
            key_vector2d("CTRL_C_jaw", frame, 0, -0.15)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_funnelU", frame, 0.5)
                key_scalar(s + "mouth_funnelD", frame, 0.5)
                key_scalar(s + "mouth_purseU", frame, 0.7)
                key_scalar(s + "mouth_purseD", frame, 0.7)
                key_scalar(s + "mouth_tightenU", frame, 0.5)
                key_scalar(s + "mouth_tightenD", frame, 0.5)

        p(f"  Frame {frame:3d}: {name:3s} - {desc} OK")

    except Exception as e:
        errors.append(f"Frame {frame} ({name}): {e}")
        p(f"  Frame {frame:3d}: {name:3s} - ERROR: {e}")

# ── 7. Verify by reading back CTRL_C_jaw.Y ──
p(f"\n=== VERIFICATION ===")
channels = face_section.get_all_channels()
for ch in channels:
    ch_name = ch.get_name()
    if "CTRL_C_jaw.Y" in ch_name:
        keys = ch.get_keys()
        p(f"{ch_name}: {len(keys)} keys")
        for k in keys:
            fv = k.get_time().frame_number.value
            val = k.get_value()
            p(f"  display_frame={fv}, jaw_Y={val:.3f}")
        break

# Also check a scalar channel
for ch in channels:
    ch_name = ch.get_name()
    if "mouth_pressU" in ch_name and "CTRL_L" in ch_name:
        keys = ch.get_keys()
        p(f"\n{ch_name}: {len(keys)} keys")
        for k in keys:
            fv = k.get_time().frame_number.value
            val = k.get_value()
            p(f"  display_frame={fv}, val={val:.3f}")
        break

if errors:
    p(f"\n{len(errors)} errors:")
    for e in errors:
        p(f"  {e}")
else:
    p(f"\nAll 15 visemes keyed successfully!")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
