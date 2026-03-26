"""Check parameter names and try to clean up duplicate parameters."""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
face_section = None
face_track = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            face_track = track
            sections = track.get_sections()
            if sections:
                face_section = sections[0]
                break
    if face_section: break

# Get parameter names
try:
    params = face_section.get_parameter_names()
    p(f"Parameter names: {len(params)}")
    for name in list(params)[:30]:
        p(f"  {name}")
    if len(params) > 30:
        p(f"  ... ({len(params)-30} more)")
except Exception as e:
    p(f"get_parameter_names error: {e}")

# Try removing ALL scalar parameters and re-adding cleanly
# First, count channels before
channels_before = len(face_section.get_all_channels())
p(f"\nChannels before cleanup: {channels_before}")

# Try removing a specific stale parameter
try:
    face_section.remove_scalar_parameter("CTRL_C_jaw_fwdBack")
    p("remove_scalar_parameter('CTRL_C_jaw_fwdBack') -> OK")
except Exception as e:
    p(f"remove_scalar_parameter: {e}")

try:
    face_section.remove_vector2d_parameter("CTRL_C_jaw")
    p("remove_vector2d_parameter('CTRL_C_jaw') -> OK")
except Exception as e:
    p(f"remove_vector2d_parameter: {e}")

channels_after = len(face_section.get_all_channels())
p(f"Channels after remove: {channels_after}")

# Alternative approach: delete the entire section and recreate
p(f"\n=== Track info ===")
p(f"Track sections: {len(face_track.get_sections())}")
p(f"Track type: {type(face_track).__name__}")

# Check section_to_key
try:
    stk = face_track.get_section_to_key()
    p(f"Section to key: {stk}")
except Exception as e:
    p(f"get_section_to_key: {e}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
