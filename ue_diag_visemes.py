"""Diagnose current state of viseme keys in the FaceExport level sequence."""
import unreal

out = []

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
if not level_seq:
    out.append("ERROR: No level sequence open")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
    raise SystemExit

out.append(f"Level Sequence: {level_seq.get_name()}")
out.append(f"Path: {level_seq.get_path_name()}")

# List all bindings and tracks
face_section = None
out.append("\n=== BINDINGS ===")
for binding in level_seq.get_bindings():
    bname = binding.get_display_name()
    out.append(f"Binding: {bname}")
    for track in binding.get_tracks():
        tname = str(track.get_display_name())
        sections = track.get_sections()
        out.append(f"  Track: {tname} ({len(sections)} sections)")
        if "Face_ControlBoard" in tname and sections:
            face_section = sections[0]

if not face_section:
    out.append("\nERROR: No Face_ControlBoard_CtrlRig section found")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
    raise SystemExit

# Check channels with keys
channels = face_section.get_all_channels()
out.append(f"\n=== CHANNELS: {len(channels)} total ===")

keyed_channels = []
for ch in channels:
    try:
        nkeys = ch.get_num_keys()
        if nkeys > 0:
            keyed_channels.append((ch.get_name(), nkeys))
    except:
        pass

out.append(f"Channels with keys: {len(keyed_channels)}")
for name, nk in sorted(keyed_channels):
    out.append(f"  {name}: {nk} keys")

# Check jaw.Y specifically for viseme frames
out.append("\n=== JAW.Y KEY VALUES ===")
for ch in channels:
    if "CTRL_C_jaw.Y" in ch.get_name():
        keys = ch.get_keys()
        for k in keys:
            frame = k.get_time().frame_number.value
            val = k.get_value()
            out.append(f"  frame={frame} jaw_Y={val:.3f}")
        break

# Check mouth_pressU for PP viseme
out.append("\n=== CTRL_L_mouth_pressU KEYS ===")
for ch in channels:
    if "mouth_pressU" in ch.get_name() and "CTRL_L" in ch.get_name():
        keys = ch.get_keys()
        for k in keys:
            frame = k.get_time().frame_number.value
            val = k.get_value()
            out.append(f"  frame={frame} val={val:.3f}")
        break

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
