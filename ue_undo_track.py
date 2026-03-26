"""Try to undo the track deletion and parameter removal via transaction system."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# First remove the broken empty track we just added
face_binding = None
for b in level_seq.get_bindings():
    if b.get_display_name() == "Face":
        face_binding = b
        break

for t in list(face_binding.get_tracks()):
    face_binding.remove_track(t)
    out.append(f"Removed broken track: {t.get_display_name()}")

# Try GEditor.undo via various methods
try:
    unreal.SystemLibrary.execute_console_command(None, "TRANSACTION UNDO")
    out.append("Executed TRANSACTION UNDO")
except Exception as e:
    out.append(f"Console UNDO failed: {e}")

# Try the editor subsystem
try:
    subsys = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    out.append(f"Editor subsystem: {subsys}")
except:
    pass

# Check tracks on Face binding after undo attempt
tracks = list(face_binding.get_tracks())
out.append(f"\nFace binding tracks: {len(tracks)}")
for t in tracks:
    out.append(f"  {t.get_display_name()}")
    for s in t.get_sections():
        out.append(f"    Channels: {len(s.get_all_channels())}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
