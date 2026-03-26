"""
Nuclear option: remove the corrupted Face_ControlBoard section,
add a fresh one, and key visemes on the clean channels.
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

face_track = None
face_binding = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            face_track = track
            face_binding = binding
            break
    if face_track: break

if not face_track:
    p("ERROR: Face_ControlBoard track not found")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
    raise SystemExit

# Remove old section(s)
old_sections = face_track.get_sections()
p(f"Removing {len(old_sections)} old section(s)")
for sec in old_sections:
    face_track.remove_section(sec)
    p(f"  Removed section")

# Add a new fresh section
new_section = face_track.add_section()
p(f"New section: {type(new_section).__name__}")

# Set section range
TICKS = 800
try:
    new_section.set_start_frame_bounded(True)
    new_section.set_start_frame(0)
    new_section.set_end_frame_bounded(True)
    new_section.set_end_frame(150 * TICKS)
    p("Section range: 0-150 frames")
except Exception as e:
    p(f"Set range error: {e}")

# Check initial channel count
channels = new_section.get_all_channels()
p(f"Initial channels: {len(channels)}")

# Check if it has the control rig class set
try:
    crc = new_section.get_editor_property('control_rig_class')
    p(f"control_rig_class: {crc}")
except Exception as e:
    p(f"control_rig_class: {e}")

# Key a test value
try:
    fn = unreal.FrameNumber(100 * TICKS)
    new_section.add_vector2d_parameter_key("CTRL_C_jaw", fn, unreal.Vector2D(0, -0.7))
    p("Keyed CTRL_C_jaw at frame 100 -> OK")
except Exception as e:
    p(f"Key error: {e}")

# Check channels after keying
channels = new_section.get_all_channels()
p(f"Channels after keying: {len(channels)}")
for ch in channels:
    name = ch.get_name()
    nk = ch.get_num_keys()
    if nk > 0:
        p(f"  {name}: {nk} keys")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
