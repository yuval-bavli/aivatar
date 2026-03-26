"""Check binding status — simplified."""
import unreal

out = []
try:
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
    lib = unreal.ControlRigSequencerLibrary

    for b in level_seq.get_bindings():
        name = b.get_display_name()
        tracks = list(b.get_tracks())
        out.append(f"Binding '{name}': {len(tracks)} tracks")
        for t in tracks:
            out.append(f"  Track: {t.get_display_name()} ({type(t).__name__})")
            sections = t.get_sections()
            for s in sections:
                chs = s.get_all_channels()
                keyed = sum(1 for ch in chs if ch.get_num_keys() > 0)
                out.append(f"  Section: {len(chs)} channels, {keyed} with keys")

    # API readback at display frame 100
    rigs = lib.get_control_rigs(level_seq)
    for proxy in rigs:
        cr = proxy.control_rig
        if "Face" in cr.get_name():
            val = lib.get_local_control_rig_float(level_seq, cr, "CTRL_C_jaw_openExtreme",
                unreal.FrameNumber(100), time_unit=unreal.MovieSceneTimeUnit.DISPLAY_RATE)
            out.append(f"\njaw_openExtreme at display frame 100: {val}")

            val2 = lib.get_local_control_rig_vector2d(level_seq, cr, "CTRL_C_jaw",
                unreal.FrameNumber(100), time_unit=unreal.MovieSceneTimeUnit.DISPLAY_RATE)
            out.append(f"jaw at display frame 100: {val2}")
            break
except Exception as e:
    out.append(f"ERROR: {e}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
