"""
Delete the face control rig track and re-add it to get clean parameter registrations.
"""
import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# Find face binding and track
face_binding = None
face_track = None
for b in level_seq.get_bindings():
    if b.get_display_name() == "Face":
        face_binding = b
        for t in b.get_tracks():
            if "Face_ControlBoard" in str(t.get_display_name()):
                face_track = t
                break
        break

if not face_binding or not face_track:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: Face binding/track not found")
    raise SystemExit

out.append(f"Found binding: {face_binding.get_display_name()}")
out.append(f"Found track: {face_track.get_display_name()}")

# Remove the track
try:
    face_binding.remove_track(face_track)
    out.append("Track removed!")
except Exception as e:
    out.append(f"remove_track failed: {e}")
    # Try alternative: remove via level_seq
    try:
        level_seq.remove_track(face_track)
        out.append("Track removed via level_seq!")
    except Exception as e2:
        out.append(f"level_seq.remove_track also failed: {e2}")

# Check what's left
tracks_left = []
for t in face_binding.get_tracks():
    tracks_left.append(t.get_display_name())
out.append(f"Tracks remaining on Face binding: {tracks_left}")

# Now re-add the control rig track
# The control rig should auto-bind when we use the library
rigs = lib.get_control_rigs(level_seq)
out.append(f"Control rigs found: {len(rigs)}")
for r in rigs:
    out.append(f"  {r.control_rig.get_name()}")

# Check channels
for t in face_binding.get_tracks():
    if "Face_ControlBoard" in str(t.get_display_name()):
        section = t.get_sections()[0]
        channels = section.get_all_channels()
        out.append(f"\nNew track channels: {len(channels)}")
        keyed = sum(1 for ch in channels if list(ch.get_keys()))
        out.append(f"Channels with keys: {keyed}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
