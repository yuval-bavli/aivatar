"""Test extreme jaw opening to verify controls respond."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

TICKS = 800

# Find jaw.Y channel
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            section = t.get_sections()[0]
            for ch in section.get_all_channels():
                name = ch.get_name()
                if 'jaw.Y' in name:
                    out.append(f"Channel: {name}")
                    keys = list(ch.get_keys())
                    # Find key at frame 30
                    for k in keys:
                        f = k.get_time().frame_number.value
                        if f == 30 * TICKS:
                            old_val = k.get_value()
                            k.set_value(-5.0)
                            out.append(f"Changed jaw.Y at frame 30 from {old_val} to -5.0")
                            break
                    break
            break

# Force scrub to frame 30
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30)
out.append("Scrubbed to frame 30")

# Also check: does force_evaluate exist?
try:
    unreal.LevelSequenceEditorBlueprintLibrary.play()
    import time
    # Can't use time.sleep in UE, but play briefly then stop
    out.append("Started playback")
except Exception as e:
    out.append(f"play error: {e}")

try:
    unreal.LevelSequenceEditorBlueprintLibrary.pause()
    out.append("Paused")
except Exception as e:
    out.append(f"pause error: {e}")

try:
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30)
    out.append("Re-scrubbed to frame 30")
except Exception as e:
    out.append(f"scrub error: {e}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
