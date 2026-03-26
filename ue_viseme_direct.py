"""
Key 15 Azure viseme poses directly on the control rig's BOUND channels.
Instead of add_scalar_parameter_key (which creates separate parameter curves),
we find the existing bound channels and add keys directly to them.
"""
import unreal

out = []

# ── 1. Find face section ──
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
if not level_seq:
    out.append("ERROR: No Level Sequence open")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
    raise SystemExit

out.append(f"Level Sequence: {level_seq.get_name()}")

face_section = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            face_section = track.get_sections()[0]
            break

if not face_section:
    out.append("ERROR: Face section not found")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
    raise SystemExit

# ── 2. Build channel lookup ──
# Channels from the control rig binding have names like "CTRL_C_jaw.Y_0"
# We strip the trailing _N suffix to get the control name
channels = face_section.get_all_channels()
out.append(f"Total channels: {len(channels)}")

ch_map = {}  # control_name -> channel object
for ch in channels:
    name = ch.get_name()
    # Strip trailing _N suffix (e.g., "CTRL_C_jaw.Y_0" -> "CTRL_C_jaw.Y")
    parts = name.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        base = parts[0]
    else:
        base = name
    # Only keep the FIRST (lowest suffix) channel for each base name
    # These are the original bound channels, not parameter-created ones
    if base not in ch_map:
        ch_map[base] = ch

out.append(f"Unique channel bases: {len(ch_map)}")

# Verify we have the key channels
test_channels = ["CTRL_C_jaw.Y", "CTRL_L_mouth_stretch", "CTRL_C_tongue_inOut"]
for tc in test_channels:
    if tc in ch_map:
        out.append(f"  Found: {tc} -> {ch_map[tc].get_name()}")
    else:
        out.append(f"  MISSING: {tc}")

# ── 3. Clear all existing keys from ALL channels ──
out.append("\nClearing keys from all channels...")
cleared = 0
for ch in channels:
    try:
        keys = ch.get_keys()
        key_list = list(keys)
        if len(key_list) > 0:
            for k in reversed(key_list):
                ch.remove_key(k)
            cleared += 1
    except:
        pass
out.append(f"Cleared {cleared} channels")

# ── 4. Key helpers ──
TICKS_PER_FRAME = 800

def key_ch(name, frame, value):
    """Add a key on a bound channel."""
    if name not in ch_map:
        return False
    ch = ch_map[name]
    fn = unreal.FrameNumber(frame * TICKS_PER_FRAME)
    ch.add_key(fn, float(value))
    return True

errors = []

def key_scalar(name, frame, value):
    if not key_ch(name, frame, value):
        errors.append(f"Channel not found: {name}")

def key_vector2d_xy(name, frame, x, y):
    """Key X and Y sub-channels of a 2D control."""
    key_ch(name + ".X", frame, x)
    key_ch(name + ".Y", frame, y)

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
    """Reset all mouth controls at a frame."""
    key_vector2d_xy("CTRL_C_jaw", frame, 0, 0)
    key_scalar("CTRL_C_jaw_fwdBack", frame, 0)
    key_scalar("CTRL_C_jaw_openExtreme", frame, 0)
    key_vector2d_xy("CTRL_C_mouth", frame, 0, 0)
    for side in ["CTRL_L_", "CTRL_R_"]:
        for ctrl in [
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
        ]:
            key_scalar(side + ctrl, frame, 0)
    key_scalar("CTRL_C_tongue_inOut", frame, 0)
    key_scalar("CTRL_C_tongue_press", frame, 0)

# ── 6. Key each viseme ──
out.append("\nKeying visemes on bound channels...")

for frame, name, desc in VISEMES:
    try:
        key_all_zero(frame)

        if name == "sil":
            pass

        elif name == "PP":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.05)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_pressU", frame, 0.8)
                key_scalar(s + "mouth_pressD", frame, 0.8)
                key_scalar(s + "mouth_tightenU", frame, 0.5)
                key_scalar(s + "mouth_tightenD", frame, 0.5)

        elif name == "FF":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.15)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lipsRollD", frame, 0.7)
                key_scalar(s + "mouth_lipBiteU", frame, 0.6)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.2)

        elif name == "TH":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.25)
            key_scalar("CTRL_C_tongue_inOut", frame, 0.4)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.3)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.2)

        elif name == "DD":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.35)
            key_scalar("CTRL_C_tongue_press", frame, 0.5)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.3)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.15)

        elif name == "kk":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.3)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.25)

        elif name == "CH":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.15)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_funnelU", frame, 0.6)
                key_scalar(s + "mouth_funnelD", frame, 0.6)
                key_scalar(s + "mouth_purseU", frame, 0.3)
                key_scalar(s + "mouth_purseD", frame, 0.3)
                key_scalar(s + "mouth_tightenU", frame, 0.3)
                key_scalar(s + "mouth_tightenD", frame, 0.3)

        elif name == "SS":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.08)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_stretch", frame, 0.6)
                key_scalar(s + "mouth_stretchLipsClose", frame, 0.4)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.1)

        elif name == "nn":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.15)
            key_scalar("CTRL_C_tongue_press", frame, 0.4)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.15)

        elif name == "RR":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.2)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_funnelU", frame, 0.35)
                key_scalar(s + "mouth_funnelD", frame, 0.35)
                key_scalar(s + "mouth_purseU", frame, 0.15)
                key_scalar(s + "mouth_purseD", frame, 0.15)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.15)

        elif name == "aa":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.7)
            key_scalar("CTRL_C_jaw_openExtreme", frame, 0.3)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.6)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.4)
                key_scalar(s + "mouth_stretch", frame, 0.3)
                key_scalar(s + "mouth_cornerDepress", frame, 0.2)

        elif name == "E":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.4)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_stretch", frame, 0.45)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.35)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.2)
                key_scalar(s + "mouth_cornerPull", frame, 0.15)

        elif name == "ih":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.15)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_stretch", frame, 0.7)
                key_scalar(s + "mouth_cornerPull", frame, 0.35)
                key_scalar(s + "mouth_lowerLipDepress", frame, 0.15)
                key_scalar(s + "mouth_upperLipRaise", frame, 0.1)

        elif name == "oh":
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.4)
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
            key_vector2d_xy("CTRL_C_jaw", frame, 0, -0.15)
            for s in ["CTRL_L_", "CTRL_R_"]:
                key_scalar(s + "mouth_funnelU", frame, 0.5)
                key_scalar(s + "mouth_funnelD", frame, 0.5)
                key_scalar(s + "mouth_purseU", frame, 0.7)
                key_scalar(s + "mouth_purseD", frame, 0.7)
                key_scalar(s + "mouth_tightenU", frame, 0.5)
                key_scalar(s + "mouth_tightenD", frame, 0.5)

        out.append(f"  Frame {frame:3d}: {name:3s} - {desc} OK")

    except Exception as e:
        out.append(f"  Frame {frame:3d}: {name:3s} - ERROR: {e}")
        errors.append(str(e))

# ── 7. Verify ──
out.append(f"\n=== VERIFICATION ===")
if "CTRL_C_jaw.Y" in ch_map:
    ch = ch_map["CTRL_C_jaw.Y"]
    keys = ch.get_keys()
    out.append(f"{ch.get_name()}: {len(keys)} keys")
    for k in keys:
        f = k.get_time().frame_number.value
        v = k.get_value()
        out.append(f"  frame={f} val={v:.3f}")

if errors:
    unique_errors = list(set(errors))
    out.append(f"\n{len(unique_errors)} unique errors:")
    for e in unique_errors[:10]:
        out.append(f"  {e}")
else:
    out.append(f"\nAll 15 visemes keyed successfully on bound channels!")

# Scrub to aa for visual check
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(100 * TICKS_PER_FRAME)
out.append("\nScrubbed to frame 100 (aa)")

out.append("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
