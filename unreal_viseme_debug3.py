"""
Diagnostic: specifically select Face_ControlBoard_CtrlRig and list its channels.
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
if not level_seq:
    p("ERROR: No Level Sequence open"); raise SystemExit

p(f"Level Sequence: {level_seq.get_name()}")

face_section = None
body_section = None

for binding in level_seq.get_bindings():
    bname = binding.get_display_name()
    for track in binding.get_tracks():
        tname = str(track.get_display_name())
        sections = track.get_sections()
        p(f"Binding='{bname}' Track='{tname}' sections={len(sections)}")
        if "Face_ControlBoard" in tname and sections:
            face_section = sections[0]
            p("  -> SELECTED as FACE section")
        elif "MetaHuman_ControlRig" in tname and sections:
            body_section = sections[0]
            p("  -> body section (skipped)")

if not face_section:
    p("ERROR: Face_ControlBoard_CtrlRig not found")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
    raise SystemExit

channels = face_section.get_all_channels()
p(f"\n=== FACE CHANNELS ({len(channels)}) ===")

jaw_ch = []
mouth_ch = []
tongue_ch = []
ctrl_ch = []
other_ch = []

for ch in channels:
    ch_name = ch.get_name()
    ch_type = type(ch).__name__
    try:
        nkeys = ch.get_num_keys()
    except:
        nkeys = "?"
    line = f"{ch_name} ({ch_type}) [{nkeys} keys]"
    nl = ch_name.lower()
    if "jaw" in nl:
        jaw_ch.append(line)
    elif "mouth" in nl or "lip" in nl:
        mouth_ch.append(line)
    elif "tongue" in nl:
        tongue_ch.append(line)
    elif "ctrl" in nl:
        ctrl_ch.append(line)
    else:
        other_ch.append(line)

p(f"\n--- JAW ({len(jaw_ch)}) ---")
for c in sorted(jaw_ch): p(f"  {c}")
p(f"\n--- MOUTH/LIP ({len(mouth_ch)}) ---")
for c in sorted(mouth_ch): p(f"  {c}")
p(f"\n--- TONGUE ({len(tongue_ch)}) ---")
for c in sorted(tongue_ch): p(f"  {c}")
p(f"\n--- CTRL (other) ({len(ctrl_ch)}) ---")
for c in sorted(ctrl_ch)[:60]: p(f"  {c}")
if len(ctrl_ch) > 60: p(f"  ... and {len(ctrl_ch)-60} more")
p(f"\n--- OTHER ({len(other_ch)}) ---")
for c in sorted(other_ch)[:30]: p(f"  {c}")
if len(other_ch) > 30: p(f"  ... and {len(other_ch)-30} more")

# Channels with keys
p(f"\n=== CHANNELS WITH EXISTING KEYS ===")
found_keys = False
for ch in channels:
    try:
        nkeys = ch.get_num_keys()
        if nkeys > 0:
            found_keys = True
            ch_name = ch.get_name()
            p(f"{ch_name}: {nkeys} keys")
            keys = ch.get_keys()
            for k in keys[:15]:
                fv = k.get_time().frame_number.value
                try: val = k.get_value()
                except: val = "?"
                p(f"  tick={fv}, val={val}")
    except:
        pass
if not found_keys:
    p("(none)")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
