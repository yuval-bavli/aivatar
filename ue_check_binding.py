"""Check if the control rig track is properly bound and evaluating."""
import unreal

out = []
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# Check all bindings and their tracks
for b in level_seq.get_bindings():
    name = b.get_display_name()
    tracks = list(b.get_tracks())
    track_names = [str(t.get_display_name()) for t in tracks]
    if 'Face' in name or 'Control' in str(track_names):
        out.append(f"Binding: {name}")
        out.append(f"  Tracks ({len(tracks)}):")
        for t in tracks:
            out.append(f"    {t.get_display_name()} - type: {type(t).__name__}")
            # Check if track has control rig reference
            try:
                cr = t.get_editor_property("control_rig")
                out.append(f"    CR ref: {cr}")
            except:
                pass
            # Check sections
            for s in t.get_sections():
                ch_count = len(s.get_all_channels())
                keyed = sum(1 for ch in s.get_all_channels() if len(list(ch.get_keys())) > 0)
                out.append(f"    Section: {ch_count} channels, {keyed} with keys")

# Check if the sequence is being evaluated
try:
    is_playing = unreal.LevelSequenceEditorBlueprintLibrary.is_playing()
    out.append(f"\nIs playing: {is_playing}")
except:
    pass

# Check the control rigs bound to the sequence
lib = unreal.ControlRigSequencerLibrary
rigs = lib.get_control_rigs(level_seq)
out.append(f"\nControl rigs: {len(rigs)}")
for proxy in rigs:
    cr = proxy.control_rig
    out.append(f"  {cr.get_name()} - class: {type(cr).__name__}")

# Try to force evaluate by toggling playback
out.append("\nTrying to force evaluate...")
try:
    unreal.LevelSequenceEditorBlueprintLibrary.play()
    out.append("  Play: OK")
except Exception as e:
    out.append(f"  Play failed: {e}")

try:
    unreal.LevelSequenceEditorBlueprintLibrary.pause()
    out.append("  Pause: OK")
except Exception as e:
    out.append(f"  Pause failed: {e}")

# Scrub to frame 100 to check aa
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(100)
out.append("  Scrubbed to frame 100")

# Read back rig value at current time
try:
    val = lib.get_local_control_rig_float(level_seq, rigs[0].control_rig, "CTRL_C_jaw_openExtreme",
        unreal.FrameNumber(100), time_unit=unreal.MovieSceneTimeUnit.DISPLAY_RATE)
    out.append(f"  jaw_openExtreme at frame 100 (API readback): {val}")
except Exception as e:
    out.append(f"  API readback error: {e}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
