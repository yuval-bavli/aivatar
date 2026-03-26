"""
Test: find the correct FrameNumber scale for keying.
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
face_section = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            sections = track.get_sections()
            if sections:
                face_section = sections[0]
                break
    if face_section:
        break

if not face_section:
    p("ERROR: Face_ControlBoard not found")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
    raise SystemExit

# First, clear CTRL_C_jaw_openExtreme by removing all keys
# We'll use a channel we can read back easily
# Key at various FrameNumber values and read back
test_values = [
    (0, 0.1),
    (1, 0.2),
    (10, 0.3),
    (30, 0.4),
    (100, 0.5),
    (300, 0.6),
    (800, 0.7),
    (8000, 0.8),
    (24000, 0.9),
]

# Use a channel we haven't used much: CTRL_C_neck_swallow
p("Keying CTRL_C_neck_swallow at various FrameNumbers...")
for fn_val, scalar_val in test_values:
    fn = unreal.FrameNumber(fn_val)
    try:
        face_section.add_scalar_parameter_key("CTRL_C_neck_swallow", fn, scalar_val)
        p(f"  FrameNumber({fn_val}) val={scalar_val} -> OK")
    except Exception as e:
        p(f"  FrameNumber({fn_val}) val={scalar_val} -> ERROR: {e}")

# Read back
for ch in face_section.get_all_channels():
    if "neck_swallow" in ch.get_name():
        keys = ch.get_keys()
        p(f"\nRead back {ch.get_name()}: {len(keys)} keys")
        for k in keys:
            fv = k.get_time().frame_number.value
            val = k.get_value()
            p(f"  frame_number.value={fv}, val={val}")
        break

# Also check: what's the tick resolution?
p(f"\n--- Sequence info ---")
try:
    dr = level_seq.get_display_rate()
    p(f"Display rate: {dr}")
except: pass

try:
    # Check FrameRate
    p(f"Display rate numerator: {dr.numerator}")
    p(f"Display rate denominator: {dr.denominator}")
except: pass

# Try MovieSceneSection methods
p(f"\n--- Section methods ---")
for attr in dir(face_section):
    if 'range' in attr.lower() or 'frame' in attr.lower() or 'tick' in attr.lower() or 'time' in attr.lower():
        p(f"  {attr}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
