"""List all methods on the face section to find parameter mask/mapping APIs."""
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

# Section methods
p("=== MovieSceneControlRigParameterSection methods ===")
all_m = sorted([m for m in dir(face_section) if not m.startswith('_')])
for m in all_m:
    p(f"  {m}")

# Track methods
p(f"\n=== MovieSceneControlRigParameterTrack methods ===")
all_t = sorted([m for m in dir(face_track) if not m.startswith('_')])
for m in all_t:
    p(f"  {m}")

# Check if section has scalar/vector parameter lists
p(f"\n=== Parameter inspection ===")
try:
    # Try to list parameter names
    p(f"get_scalar_parameter_names: {face_section.get_scalar_parameter_names()}")
except Exception as e:
    p(f"get_scalar_parameter_names: {e}")

try:
    p(f"get_vector2d_parameter_names: {face_section.get_vector2d_parameter_names()}")
except Exception as e:
    p(f"get_vector2d_parameter_names: {e}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
