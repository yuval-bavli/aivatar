"""
Step 1: Delete the Face_ControlBoard track
Step 2: Recreate it via find_or_create_control_rig_track
Step 3: Run the viseme keying pass
"""
import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

if not level_seq:
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("ERROR: No level sequence open")
    raise SystemExit

# Step 1: Find and delete the existing Face_ControlBoard track
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

if face_track:
    face_binding.remove_track(face_track)
    out.append("Deleted existing Face_ControlBoard track")
else:
    out.append("No Face_ControlBoard track found to delete")

if not face_binding:
    out.append("ERROR: No Face binding found")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
    raise SystemExit

# Step 2: Recreate the track
cr_bp = unreal.load_asset("/Game/MetaHumans/Common/Face/Face_ControlBoard_CtrlRig")
out.append(f"CR Blueprint: {cr_bp.get_name() if cr_bp else 'None'}")

cr_class = None
try:
    cr_class = cr_bp.generated_class()
except:
    try:
        cr_class = cr_bp.get_editor_property("generated_class")
    except:
        pass

if not cr_class:
    out.append("ERROR: Could not get CR class")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
    raise SystemExit

out.append(f"CR Class: {cr_class}")

try:
    result = lib.find_or_create_control_rig_track(level_seq, cr_class, face_binding)
    out.append(f"Track recreated: {result}")
except Exception as e:
    out.append(f"find_or_create failed: {e}")
    try:
        world = unreal.EditorLevelLibrary.get_editor_world()
        result = lib.find_or_create_control_rig_track(world, level_seq, cr_class, face_binding)
        out.append(f"Track recreated (with world): {result}")
    except Exception as e2:
        out.append(f"With world also failed: {e2}")

# Verify track exists now
for b in level_seq.get_bindings():
    if b.get_display_name() == "Face":
        for t in b.get_tracks():
            if "Face_ControlBoard" in str(t.get_display_name()):
                sections = t.get_sections()
                if sections:
                    ch_count = len(sections[0].get_all_channels())
                    out.append(f"New track has {ch_count} channels")
                break

# Get face rig
rigs = lib.get_control_rigs(level_seq)
face_rig = None
for proxy in rigs:
    cr = proxy.control_rig
    if "Face" in cr.get_name():
        face_rig = cr
        break

if not face_rig:
    out.append("ERROR: Face rig not found after track recreation")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
    raise SystemExit

out.append(f"Face rig: {face_rig.get_name()}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
