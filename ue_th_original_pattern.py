"""
Key TH jaw opening using the EXACT same pattern as the original working script.
The original script scrubs to frame*800 (out of bounds) then keys — and it works.
"""
import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

rigs = lib.get_control_rigs(level_seq)
face_rig = None
for proxy in rigs:
    cr = proxy.control_rig
    if "Face" in cr.get_name():
        face_rig = cr
        break

TICKS = 800
TR = unreal.MovieSceneTimeUnit.TICK_RESOLUTION
frame = 30

# Step 1: Remove existing jaw_openExtreme key at frame 30
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                if 'openExtreme' in ch.get_name():
                    keys = list(ch.get_keys())
                    for k in keys:
                        if k.get_time().frame_number.value == frame:
                            ch.remove_key(k)
                            out.append(f"Removed key at frame {frame}, old val={k.get_value():.4f}")
                    # Show remaining keys
                    keys2 = list(ch.get_keys())
                    out.append(f"Keys remaining: {len(keys2)}")
                    break
            break

# Step 2: Scrub using EXACT same pattern as original script
# Original: unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)
out.append(f"Scrubbed to {frame * TICKS}")

# Step 3: Key using EXACT same pattern
lib.set_local_control_rig_float(level_seq, face_rig, "CTRL_C_jaw_openExtreme",
    unreal.FrameNumber(frame * TICKS), 1.0, time_unit=TR, set_key=True)
out.append("Keyed jaw_openExtreme=1.0")

# Step 4: Verify via channel
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                if 'openExtreme' in ch.get_name():
                    keys = list(ch.get_keys())
                    out.append(f"\nChannel {ch.get_name()}: {len(keys)} keys")
                    for k in keys:
                        out.append(f"  frame={k.get_time().frame_number.value} val={k.get_value():.4f}")
                    break
            break

# Step 5: Scrub to frame 30 (display rate) for visual
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30)
out.append("\nScrubbed to display frame 30")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
