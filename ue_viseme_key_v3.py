"""
Key 15 Azure viseme poses using ControlRigSequencerLibrary.
v3: Uses TICK_RESOLUTION (not DISPLAY_RATE which is broken).
Groups keys by control to minimize channel creation.
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
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: Face rig not found")
    raise SystemExit

out.append(f"Face rig: {face_rig.get_name()}")

# Clear ALL existing keys from the section
face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            break

if face_section:
    channels = face_section.get_all_channels()
    cleared = 0
    for ch in channels:
        try:
            keys = list(ch.get_keys())
            if keys:
                for k in reversed(keys):
                    ch.remove_key(k)
                cleared += 1
        except:
            pass
    out.append(f"Cleared keys from {cleared} channels")

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

# Define viseme poses: frame -> {control: value}
# tuple = vec2d, scalar = float
viseme_poses = {
    0: {  # sil - rest
        "CTRL_C_jaw": (0, 0),
    },
    10: {  # PP - lips pressed
        "CTRL_C_jaw": (0, -0.05),
        "CTRL_L_mouth_pressU": 0.8, "CTRL_R_mouth_pressU": 0.8,
        "CTRL_L_mouth_pressD": 0.8, "CTRL_R_mouth_pressD": 0.8,
        "CTRL_L_mouth_tightenU": 0.5, "CTRL_R_mouth_tightenU": 0.5,
        "CTRL_L_mouth_tightenD": 0.5, "CTRL_R_mouth_tightenD": 0.5,
    },
    20: {  # FF - lower lip under teeth
        "CTRL_C_jaw": (0, -0.15),
        "CTRL_L_mouth_lipsRollD": 0.7, "CTRL_R_mouth_lipsRollD": 0.7,
        "CTRL_L_mouth_lipBiteU": 0.6, "CTRL_R_mouth_lipBiteU": 0.6,
        "CTRL_L_mouth_upperLipRaise": 0.2, "CTRL_R_mouth_upperLipRaise": 0.2,
    },
    30: {  # TH - tongue between teeth
        "CTRL_C_jaw": (0, -0.4),
        "CTRL_C_tongue_inOut": 0.9,
        "CTRL_C_tongue_tipMove": (0, 0.5),
        "CTRL_C_tongue_thickThin": -0.3,
        "CTRL_L_mouth_lowerLipDepress": 0.4, "CTRL_R_mouth_lowerLipDepress": 0.4,
        "CTRL_L_mouth_upperLipRaise": 0.3, "CTRL_R_mouth_upperLipRaise": 0.3,
    },
    40: {  # DD - tongue behind teeth
        "CTRL_C_jaw": (0, -0.35),
        "CTRL_C_tongue_press": 0.5,
        "CTRL_L_mouth_lowerLipDepress": 0.3, "CTRL_R_mouth_lowerLipDepress": 0.3,
        "CTRL_L_mouth_upperLipRaise": 0.15, "CTRL_R_mouth_upperLipRaise": 0.15,
    },
    50: {  # kk - back tongue
        "CTRL_C_jaw": (0, -0.3),
        "CTRL_L_mouth_lowerLipDepress": 0.25, "CTRL_R_mouth_lowerLipDepress": 0.25,
    },
    60: {  # CH - rounded lips
        "CTRL_C_jaw": (0, -0.15),
        "CTRL_L_mouth_funnelU": 0.6, "CTRL_R_mouth_funnelU": 0.6,
        "CTRL_L_mouth_funnelD": 0.6, "CTRL_R_mouth_funnelD": 0.6,
        "CTRL_L_mouth_purseU": 0.3, "CTRL_R_mouth_purseU": 0.3,
        "CTRL_L_mouth_purseD": 0.3, "CTRL_R_mouth_purseD": 0.3,
        "CTRL_L_mouth_tightenU": 0.3, "CTRL_R_mouth_tightenU": 0.3,
        "CTRL_L_mouth_tightenD": 0.3, "CTRL_R_mouth_tightenD": 0.3,
    },
    70: {  # SS - teeth together spread
        "CTRL_C_jaw": (0, -0.08),
        "CTRL_L_mouth_stretch": 0.6, "CTRL_R_mouth_stretch": 0.6,
        "CTRL_L_mouth_stretchLipsClose": 0.4, "CTRL_R_mouth_stretchLipsClose": 0.4,
        "CTRL_L_mouth_lowerLipDepress": 0.1, "CTRL_R_mouth_lowerLipDepress": 0.1,
    },
    80: {  # nn - tongue up relaxed
        "CTRL_C_jaw": (0, -0.15),
        "CTRL_C_tongue_press": 0.4,
        "CTRL_L_mouth_lowerLipDepress": 0.15, "CTRL_R_mouth_lowerLipDepress": 0.15,
    },
    90: {  # RR - slightly rounded
        "CTRL_C_jaw": (0, -0.2),
        "CTRL_L_mouth_funnelU": 0.35, "CTRL_R_mouth_funnelU": 0.35,
        "CTRL_L_mouth_funnelD": 0.35, "CTRL_R_mouth_funnelD": 0.35,
        "CTRL_L_mouth_purseU": 0.15, "CTRL_R_mouth_purseU": 0.15,
        "CTRL_L_mouth_purseD": 0.15, "CTRL_R_mouth_purseD": 0.15,
        "CTRL_L_mouth_lowerLipDepress": 0.15, "CTRL_R_mouth_lowerLipDepress": 0.15,
    },
    100: {  # aa - wide open
        "CTRL_C_jaw": (0, -0.7),
        "CTRL_C_jaw_openExtreme": 0.3,
        "CTRL_L_mouth_lowerLipDepress": 0.6, "CTRL_R_mouth_lowerLipDepress": 0.6,
        "CTRL_L_mouth_upperLipRaise": 0.4, "CTRL_R_mouth_upperLipRaise": 0.4,
        "CTRL_L_mouth_stretch": 0.3, "CTRL_R_mouth_stretch": 0.3,
        "CTRL_L_mouth_cornerDepress": 0.2, "CTRL_R_mouth_cornerDepress": 0.2,
    },
    110: {  # E - mid open spread
        "CTRL_C_jaw": (0, -0.4),
        "CTRL_L_mouth_stretch": 0.45, "CTRL_R_mouth_stretch": 0.45,
        "CTRL_L_mouth_lowerLipDepress": 0.35, "CTRL_R_mouth_lowerLipDepress": 0.35,
        "CTRL_L_mouth_upperLipRaise": 0.2, "CTRL_R_mouth_upperLipRaise": 0.2,
        "CTRL_L_mouth_cornerPull": 0.15, "CTRL_R_mouth_cornerPull": 0.15,
    },
    120: {  # ih - narrow spread
        "CTRL_C_jaw": (0, -0.15),
        "CTRL_L_mouth_stretch": 0.7, "CTRL_R_mouth_stretch": 0.7,
        "CTRL_L_mouth_cornerPull": 0.35, "CTRL_R_mouth_cornerPull": 0.35,
        "CTRL_L_mouth_lowerLipDepress": 0.15, "CTRL_R_mouth_lowerLipDepress": 0.15,
        "CTRL_L_mouth_upperLipRaise": 0.1, "CTRL_R_mouth_upperLipRaise": 0.1,
    },
    130: {  # oh - round open
        "CTRL_C_jaw": (0, -0.4),
        "CTRL_L_mouth_funnelU": 0.7, "CTRL_R_mouth_funnelU": 0.7,
        "CTRL_L_mouth_funnelD": 0.7, "CTRL_R_mouth_funnelD": 0.7,
        "CTRL_L_mouth_purseU": 0.2, "CTRL_R_mouth_purseU": 0.2,
        "CTRL_L_mouth_purseD": 0.2, "CTRL_R_mouth_purseD": 0.2,
        "CTRL_L_mouth_lowerLipDepress": 0.3, "CTRL_R_mouth_lowerLipDepress": 0.3,
        "CTRL_L_mouth_upperLipRaise": 0.2, "CTRL_R_mouth_upperLipRaise": 0.2,
        "CTRL_L_mouth_tightenU": 0.3, "CTRL_R_mouth_tightenU": 0.3,
        "CTRL_L_mouth_tightenD": 0.3, "CTRL_R_mouth_tightenD": 0.3,
    },
    140: {  # ou - tight pucker
        "CTRL_C_jaw": (0, -0.15),
        "CTRL_L_mouth_funnelU": 0.5, "CTRL_R_mouth_funnelU": 0.5,
        "CTRL_L_mouth_funnelD": 0.5, "CTRL_R_mouth_funnelD": 0.5,
        "CTRL_L_mouth_purseU": 0.7, "CTRL_R_mouth_purseU": 0.7,
        "CTRL_L_mouth_purseD": 0.7, "CTRL_R_mouth_purseD": 0.7,
        "CTRL_L_mouth_tightenU": 0.5, "CTRL_R_mouth_tightenU": 0.5,
        "CTRL_L_mouth_tightenD": 0.5, "CTRL_R_mouth_tightenD": 0.5,
    },
}

VISEME_NAMES = {
    0: "sil", 10: "PP", 20: "FF", 30: "TH", 40: "DD", 50: "kk",
    60: "CH", 70: "SS", 80: "nn", 90: "RR", 100: "aa", 110: "E",
    120: "ih", 130: "oh", 140: "ou"
}

out.append("\nKeying visemes...")
for frame in sorted(viseme_poses.keys()):
    controls = viseme_poses[frame]
    name = VISEME_NAMES[frame]
    for ctrl, val in controls.items():
        if isinstance(val, tuple):
            sv2(ctrl, frame, val[0], val[1])
        else:
            sf(ctrl, frame, val)
    out.append(f"  Frame {frame:3d}: {name}")

if errors:
    unique = list(set(errors))
    out.append(f"\n{len(unique)} errors:")
    for e in unique[:20]:
        out.append(f"  {e}")
else:
    out.append("\nAll 15 visemes keyed successfully!")

# Verify jaw.Y channel
if face_section:
    channels = face_section.get_all_channels()
    for ch in channels:
        if 'jaw.Y' in ch.get_name():
            keys = list(ch.get_keys())
            if keys:
                out.append(f"\nJaw.Y ({ch.get_name()}): {len(keys)} keys")
                for k in keys:
                    f = k.get_time().frame_number.value
                    v = k.get_value()
                    out.append(f"  tick={f} frame={f//800} val={v:.3f}")
                break

# Scrub to TH
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30 * TICKS)
out.append("\nScrubbed to frame 30 (TH)")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
