"""
Diagnostic: list ALL available channels on the Face ControlBoard section,
check tick resolution, and verify which keyed values actually landed.
Output goes to ue_output.txt for remote reading.
"""
import unreal, sys, io

out = io.StringIO()

def p(msg=""):
    out.write(str(msg) + "\n")

# 1. Find the level sequence and face section
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
if not level_seq:
    p("ERROR: No Level Sequence open in Sequencer")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
    raise SystemExit

p(f"Level Sequence: {level_seq.get_name()}")
try:
    dr = level_seq.get_display_rate()
    p(f"Display Rate: {dr}")
except:
    p("Display Rate: (unavailable)")

face_section = None
p("\n=== ALL BINDINGS & TRACKS ===")
for binding in level_seq.get_bindings():
    bname = binding.get_display_name()
    tracks = binding.get_tracks()
    if tracks:
        p(f"\nBinding: '{bname}' ({len(tracks)} tracks)")
    for track in tracks:
        tname = track.get_display_name()
        tclass = type(track).__name__
        sections = track.get_sections()
        p(f"  Track: '{tname}' ({tclass}), {len(sections)} sections")
        if "Control" in str(tname):
            if sections:
                face_section = sections[0]
                p(f"    *** SELECTED as face section ***")

if not face_section:
    p("\nERROR: No ControlBoard section found.")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
    raise SystemExit

# 2. Section info
p(f"\n=== FACE SECTION INFO ===")
p(f"Section type: {type(face_section).__name__}")
try:
    p(f"Start frame: {face_section.get_start_frame()}")
    p(f"End frame: {face_section.get_end_frame()}")
except Exception as e:
    p(f"Section range: error - {e}")

# 3. List ALL channels
channels = face_section.get_all_channels()
p(f"\n=== ALL CHANNELS ({len(channels)}) ===")

jaw_ch = []
mouth_ch = []
tongue_ch = []
other_ch = []

for ch in channels:
    ch_name = ch.get_name()
    ch_type = type(ch).__name__
    try:
        nkeys = ch.get_num_keys()
    except:
        nkeys = "?"
    line = f"  {ch_name} ({ch_type}) [{nkeys} keys]"

    name_lower = ch_name.lower()
    if "jaw" in name_lower:
        jaw_ch.append(line)
    elif "mouth" in name_lower or "lip" in name_lower:
        mouth_ch.append(line)
    elif "tongue" in name_lower:
        tongue_ch.append(line)
    else:
        other_ch.append(line)

p(f"\n--- JAW ({len(jaw_ch)}) ---")
for c in sorted(jaw_ch): p(c)
p(f"\n--- MOUTH/LIP ({len(mouth_ch)}) ---")
for c in sorted(mouth_ch): p(c)
p(f"\n--- TONGUE ({len(tongue_ch)}) ---")
for c in sorted(tongue_ch): p(c)
p(f"\n--- OTHER ({len(other_ch)}) ---")
for c in sorted(other_ch)[:30]: p(c)
if len(other_ch) > 30:
    p(f"  ... and {len(other_ch)-30} more")

# 4. Channels that have keys
p(f"\n=== CHANNELS WITH EXISTING KEYS ===")
for ch in channels:
    try:
        nkeys = ch.get_num_keys()
        if nkeys > 0:
            ch_name = ch.get_name()
            p(f"\n{ch_name}: {nkeys} keys")
            keys = ch.get_keys()
            for k in keys[:25]:
                fv = k.get_time().frame_number.value
                try:
                    val = k.get_value()
                except:
                    val = "?"
                p(f"  tick={fv}, val={val}")
            if nkeys > 25:
                p(f"  ... ({nkeys-25} more)")
    except:
        pass

# 5. Test keying
p(f"\n=== TEST KEYING ===")
test_fn = unreal.FrameNumber(0)
try:
    face_section.add_scalar_parameter_key("CTRL_C_jaw_fwdBack", test_fn, 0.0)
    p("add_scalar_parameter_key('CTRL_C_jaw_fwdBack', 0, 0.0) -> OK")
except Exception as e:
    p(f"CTRL_C_jaw_fwdBack error: {e}")

try:
    face_section.add_vector2d_parameter_key("CTRL_C_jaw", test_fn, unreal.Vector2D(0, 0))
    p("add_vector2d_parameter_key('CTRL_C_jaw', 0, (0,0)) -> OK")
except Exception as e:
    p(f"CTRL_C_jaw error: {e}")

# Test a bad name
try:
    face_section.add_scalar_parameter_key("CTRL_L_mouth_lipBiteU", test_fn, 0.5)
    p("add_scalar_parameter_key('CTRL_L_mouth_lipBiteU', 0, 0.5) -> OK (name accepted)")
except Exception as e:
    p(f"CTRL_L_mouth_lipBiteU error: {e}")

# Test keying at tick 8000 (frame 10 if 800 ticks/frame) and read back
p(f"\n=== TICK RESOLUTION TEST ===")
test_fn2 = unreal.FrameNumber(8000)
try:
    face_section.add_vector2d_parameter_key("CTRL_C_jaw", test_fn2, unreal.Vector2D(0, -0.99))
    p("Keyed CTRL_C_jaw at tick 8000 with Y=-0.99")
except Exception as e:
    p(f"Key at tick 8000 error: {e}")

for ch in channels:
    if "CTRL_C_jaw.Y" in ch.get_name():
        keys = ch.get_keys()
        p(f"CTRL_C_jaw.Y now has {len(keys)} keys:")
        for k in keys:
            p(f"  tick={k.get_time().frame_number.value}, val={k.get_value()}")
        break

# Clean up test key
try:
    face_section.add_vector2d_parameter_key("CTRL_C_jaw", test_fn2, unreal.Vector2D(0, 0))
except:
    pass

p("\n=== DEBUG COMPLETE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
