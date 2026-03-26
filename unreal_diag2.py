"""List which channels have keys and check if face track is evaluating."""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
face_track = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            face_track = track
            break
    if face_track: break

section = face_track.get_sections()[0]
channels = section.get_all_channels()

p(f"Total channels: {len(channels)}")
p(f"\n=== Channels WITH keys ===")
for ch in channels:
    try:
        keys = ch.get_keys()
        if len(keys) > 0:
            name = ch.get_name()
            # Show first key value
            first_val = keys[0].get_value()
            first_tick = keys[0].get_time().frame_number.value
            p(f"  {name}: {len(keys)} keys, first: tick={first_tick} val={first_val}")
    except:
        pass

# Also list first 20 channels WITHOUT keys to see the naming pattern
p(f"\n=== First 20 channels WITHOUT keys ===")
count = 0
for ch in channels:
    try:
        keys = ch.get_keys()
        if len(keys) == 0:
            p(f"  {ch.get_name()}")
            count += 1
            if count >= 20:
                break
    except:
        pass

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
