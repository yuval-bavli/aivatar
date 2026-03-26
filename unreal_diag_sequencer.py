"""Diagnose sequencer state - check all bindings and tracks in FaceExport."""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

# Find FaceExport level sequence
level_seq = None
try:
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
    p(f"Current sequence: {level_seq.get_name()}")
except:
    p("No sequence currently open in editor")

if level_seq:
    bindings = level_seq.get_bindings()
    p(f"Bindings: {len(bindings)}")
    for b in bindings:
        p(f"\n  Binding: {b.get_display_name()}")
        tracks = b.get_tracks()
        p(f"    Tracks: {len(tracks)}")
        for t in tracks:
            display = t.get_display_name()
            sections = t.get_sections()
            p(f"    Track: {display} ({len(sections)} sections)")
            for i, sec in enumerate(sections):
                channels = sec.get_all_channels()
                try:
                    start = sec.get_start_frame()
                    end = sec.get_end_frame()
                    p(f"      Section {i}: frames {start}-{end}, {len(channels)} channels")
                except:
                    p(f"      Section {i}: {len(channels)} channels (unbounded)")

                # Check if any channels have keys
                keyed = 0
                for ch in channels:
                    try:
                        keys = ch.get_keys()
                        if len(keys) > 0:
                            keyed += 1
                    except:
                        pass
                p(f"      Channels with keys: {keyed}/{len(channels)}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
