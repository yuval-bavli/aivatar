"""
Viseme keyframer V2: key directly on existing rig channels using channel.add_key().
Step 1: Rebuild section fresh
Step 2: Find channels by name
Step 3: Key using channel.add_key()
"""
import unreal, io, re

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

TICKS = 800

# ── 1. Find track and rebuild section ──
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
face_track = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            face_track = track
            break
    if face_track: break

# Remove all existing sections
for sec in face_track.get_sections():
    face_track.remove_section(sec)

# Add fresh section
section = face_track.add_section()
section.set_start_frame_bounded(True)
section.set_start_frame(0)
section.set_end_frame_bounded(True)
section.set_end_frame(150 * TICKS)
p(f"Fresh section created, {len(section.get_all_channels())} channels")

# ── 2. Build channel lookup ──
ch_map = {}
for ch in section.get_all_channels():
    name = ch.get_name()
    # Strip _N suffix to get base name
    base = re.sub(r'_\d+$', '', name)
    ch_map[base] = ch

p(f"Channel bases: {len(ch_map)}")

# Verify key channels exist
for needed in ['CTRL_C_jaw.X', 'CTRL_C_jaw.Y', 'CTRL_C_jaw_openExtreme',
               'CTRL_L_mouth_cornerPull', 'CTRL_L_mouth_stretch',
               'CTRL_C_tongue_inOut']:
    if needed in ch_map:
        p(f"  {needed} -> {ch_map[needed].get_name()} OK")
    else:
        p(f"  {needed} -> MISSING!")

# ── 3. Helper: key a scalar channel at frame ──
def key(base_name, frame, value):
    ch = ch_map.get(base_name)
    if ch:
        fn = unreal.FrameNumber(frame * TICKS)
        ch.add_key(fn, float(value))

def key2d(base_name, frame, x, y):
    """Key a 2D control (X and Y channels)."""
    key(base_name + ".X", frame, x)
    key(base_name + ".Y", frame, y)

# ── 4. Key all visemes ──
VISEMES = [
    (0,   "sil"), (10,  "PP"), (20,  "FF"), (30,  "TH"), (40,  "DD"),
    (50,  "kk"),  (60,  "CH"), (70,  "SS"), (80,  "nn"), (90,  "RR"),
    (100, "aa"),  (110, "E"),  (120, "ih"), (130, "oh"), (140, "ou"),
]

# Controls to zero at every frame
zero_scalars = [
    "CTRL_C_jaw_fwdBack", "CTRL_C_jaw_openExtreme",
    "CTRL_C_tongue_inOut", "CTRL_C_tongue_press",
]
for side in ["CTRL_L_", "CTRL_R_"]:
    for ctrl in ["mouth_cornerPull", "mouth_cornerDepress", "mouth_stretch",
                 "mouth_funnelU", "mouth_funnelD", "mouth_purseU", "mouth_purseD",
                 "mouth_upperLipRaise", "mouth_lowerLipDepress",
                 "mouth_lipsRollU", "mouth_lipsRollD",
                 "mouth_pressU", "mouth_pressD", "mouth_tightenU", "mouth_tightenD",
                 "mouth_lipsBlow", "mouth_lipsPressU", "mouth_lipsPressD",
                 "mouth_stretchLipsClose", "mouth_sharpCornerPull",
                 "mouth_pushPullU", "mouth_pushPullD",
                 "mouth_lipBiteU", "mouth_lipBiteD"]:
        zero_scalars.append(side + ctrl)

for frame, name in VISEMES:
    # Zero everything
    key2d("CTRL_C_jaw", frame, 0, 0)
    key2d("CTRL_C_mouth", frame, 0, 0)
    for s in zero_scalars:
        key(s, frame, 0)

    # Set viseme-specific values
    if name == "sil":
        pass
    elif name == "PP":
        key("CTRL_C_jaw.Y", frame, -0.05)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_pressU", frame, 0.8)
            key(s+"mouth_pressD", frame, 0.8)
            key(s+"mouth_tightenU", frame, 0.5)
            key(s+"mouth_tightenD", frame, 0.5)
    elif name == "FF":
        key("CTRL_C_jaw.Y", frame, -0.15)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_lipsRollD", frame, 0.7)
            key(s+"mouth_lipBiteU", frame, 0.6)
            key(s+"mouth_upperLipRaise", frame, 0.2)
    elif name == "TH":
        key("CTRL_C_jaw.Y", frame, -0.35)
        key("CTRL_C_tongue_inOut", frame, 0.8)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_lowerLipDepress", frame, 0.3)
            key(s+"mouth_upperLipRaise", frame, 0.2)
    elif name == "DD":
        key("CTRL_C_jaw.Y", frame, -0.35)
        key("CTRL_C_tongue_press", frame, 0.5)
        key("CTRL_C_tongue_inOut", frame, 0.3)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_lowerLipDepress", frame, 0.3)
            key(s+"mouth_upperLipRaise", frame, 0.15)
    elif name == "kk":
        key("CTRL_C_jaw.Y", frame, -0.3)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_lowerLipDepress", frame, 0.25)
    elif name == "CH":
        key("CTRL_C_jaw.Y", frame, -0.15)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_funnelU", frame, 0.6)
            key(s+"mouth_funnelD", frame, 0.6)
            key(s+"mouth_purseU", frame, 0.3)
            key(s+"mouth_purseD", frame, 0.3)
            key(s+"mouth_tightenU", frame, 0.3)
            key(s+"mouth_tightenD", frame, 0.3)
    elif name == "SS":
        key("CTRL_C_jaw.Y", frame, -0.08)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_stretch", frame, 0.6)
            key(s+"mouth_stretchLipsClose", frame, 0.4)
            key(s+"mouth_lowerLipDepress", frame, 0.1)
    elif name == "nn":
        key("CTRL_C_jaw.Y", frame, -0.15)
        key("CTRL_C_tongue_press", frame, 0.4)
        key("CTRL_C_tongue_inOut", frame, 0.2)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_lowerLipDepress", frame, 0.15)
    elif name == "RR":
        key("CTRL_C_jaw.Y", frame, -0.2)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_funnelU", frame, 0.35)
            key(s+"mouth_funnelD", frame, 0.35)
            key(s+"mouth_purseU", frame, 0.15)
            key(s+"mouth_purseD", frame, 0.15)
            key(s+"mouth_lowerLipDepress", frame, 0.15)
    elif name == "aa":
        key("CTRL_C_jaw.Y", frame, -0.7)
        key("CTRL_C_jaw_openExtreme", frame, 0.3)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_lowerLipDepress", frame, 0.6)
            key(s+"mouth_upperLipRaise", frame, 0.4)
            key(s+"mouth_stretch", frame, 0.3)
            key(s+"mouth_cornerDepress", frame, 0.2)
    elif name == "E":
        key("CTRL_C_jaw.Y", frame, -0.4)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_stretch", frame, 0.45)
            key(s+"mouth_lowerLipDepress", frame, 0.35)
            key(s+"mouth_upperLipRaise", frame, 0.2)
            key(s+"mouth_cornerPull", frame, 0.15)
    elif name == "ih":
        key("CTRL_C_jaw.Y", frame, -0.15)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_stretch", frame, 0.7)
            key(s+"mouth_cornerPull", frame, 0.35)
            key(s+"mouth_lowerLipDepress", frame, 0.15)
            key(s+"mouth_upperLipRaise", frame, 0.1)
    elif name == "oh":
        key("CTRL_C_jaw.Y", frame, -0.4)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_funnelU", frame, 0.7)
            key(s+"mouth_funnelD", frame, 0.7)
            key(s+"mouth_purseU", frame, 0.2)
            key(s+"mouth_purseD", frame, 0.2)
            key(s+"mouth_lowerLipDepress", frame, 0.3)
            key(s+"mouth_upperLipRaise", frame, 0.2)
            key(s+"mouth_tightenU", frame, 0.3)
            key(s+"mouth_tightenD", frame, 0.3)
    elif name == "ou":
        key("CTRL_C_jaw.Y", frame, -0.15)
        for s in ["CTRL_L_", "CTRL_R_"]:
            key(s+"mouth_funnelU", frame, 0.5)
            key(s+"mouth_funnelD", frame, 0.5)
            key(s+"mouth_purseU", frame, 0.7)
            key(s+"mouth_purseD", frame, 0.7)
            key(s+"mouth_tightenU", frame, 0.5)
            key(s+"mouth_tightenD", frame, 0.5)

    p(f"Frame {frame:3d}: {name} OK")

# ── 5. Verify ──
jaw_y = ch_map.get("CTRL_C_jaw.Y")
if jaw_y:
    keys = jaw_y.get_keys()
    p(f"\nVerify CTRL_C_jaw.Y: {len(keys)} keys")
    for k in keys:
        tick = k.get_time().frame_number.value
        val = k.get_value()
        display_frame = tick // TICKS
        p(f"  frame {display_frame}: jaw_Y={val:.3f}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
