"""
Check what keyframes were actually placed.
Run:  exec(open("c:/Users/yuval/src/aivatar/unreal_viseme_check.py").read())
"""
import unreal

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
face_section = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "ControlBoard" in str(track.get_display_name()):
            sections = track.get_sections()
            if sections:
                face_section = sections[0]

if not face_section:
    print("ERROR: section not found"); raise SystemExit

# Check section range
print(f"Section range: {face_section.get_start_frame()} to {face_section.get_end_frame()}")

# Check a specific channel — CTRL_C_jaw should have keys at 0,10,20,...,140
channels = face_section.get_all_channels()
for ch in channels:
    ch_name = ch.get_name()
    if "CTRL_C_jaw.Y" in ch_name:
        print(f"\nChannel: {ch_name}")
        # Try to get keys
        try:
            keys = ch.get_keys()
            print(f"  Keys: {len(keys)}")
            for k in keys:
                print(f"    Frame: {k.get_time().frame_number.value}, Value: {k.get_value()}")
        except Exception as e:
            print(f"  get_keys error: {e}")
        # Try get_num_keys
        try:
            n = ch.get_num_keys()
            print(f"  Num keys: {n}")
        except Exception as e:
            print(f"  get_num_keys error: {e}")
        break

# Also check a scalar channel
for ch in channels:
    ch_name = ch.get_name()
    if "jaw_openExtreme" in ch_name:
        print(f"\nChannel: {ch_name}")
        try:
            keys = ch.get_keys()
            print(f"  Keys: {len(keys)}")
            for k in keys:
                print(f"    Frame: {k.get_time().frame_number.value}, Value: {k.get_value()}")
        except Exception as e:
            print(f"  get_keys error: {e}")
        break

print("\n=== DONE ===")
