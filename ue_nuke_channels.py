"""
Completely reset the face control rig section by removing the track
and re-adding it, eliminating all orphan channels.
"""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
lib = unreal.ControlRigSequencerLibrary

# Find the face binding and track
face_binding = None
face_track = None
for b in level_seq.get_bindings():
    bname = b.get_display_name()
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_binding = b
            face_track = t
            break
    if face_track:
        break

if not face_track:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: No face track")
    raise SystemExit

out.append(f"Found track: {face_track.get_display_name()}")
out.append(f"Binding: {face_binding.get_display_name()}")

# Get section and check for remove methods
section = face_track.get_sections()[0]
channels_before = len(section.get_all_channels())
out.append(f"Channels before: {channels_before}")

# Try to remove scalar/vector parameters from the section
# These are the methods on MovieSceneControlRigParameterSection
try:
    # Check what methods the section has
    section_type = type(section).__name__
    out.append(f"Section type: {section_type}")

    # Try removing all scalar parameters
    channels = section.get_all_channels()
    param_names = set()
    for ch in channels:
        name = ch.get_name()
        # Strip suffix like _32
        parts = name.rsplit('_', 1)
        if parts:
            param_names.add(parts[0])

    out.append(f"Unique parameter base names: {len(param_names)}")

    # Try to use remove methods
    removed = 0
    for pname in param_names:
        try:
            section.remove_scalar_parameter(pname)
            removed += 1
        except:
            pass
        try:
            section.remove_vector2d_parameter(pname)
            removed += 1
        except:
            pass
    out.append(f"Removed {removed} parameters")

except Exception as e:
    out.append(f"Error: {e}")

channels_after = len(section.get_all_channels())
out.append(f"Channels after: {channels_after}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
