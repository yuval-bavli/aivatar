"""
Diagnostic: list ALL available channels on the Face ControlBoard section,
check tick resolution, and verify which keyed values actually landed.

Run:  exec(open("c:/Users/yuval/src/aivatar/unreal_viseme_debug.py").read())
"""
import unreal

# ── 1. Find the level sequence and face section ──
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
if not level_seq:
    print("ERROR: No Level Sequence open in Sequencer"); raise SystemExit

print(f"Level Sequence: {level_seq.get_name()}")
print(f"Display Rate: {level_seq.get_display_rate()}")

# Try to get tick resolution
try:
    tr = level_seq.get_tick_resolution()
    print(f"Tick Resolution: {tr}")
except:
    print("Tick Resolution: (method unavailable)")

face_section = None
face_track = None
face_binding = None
print("\n=== ALL BINDINGS & TRACKS ===")
for binding in level_seq.get_bindings():
    bname = binding.get_display_name()
    tracks = binding.get_tracks()
    if tracks:
        print(f"\nBinding: '{bname}' ({len(tracks)} tracks)")
    for track in tracks:
        tname = track.get_display_name()
        tclass = type(track).__name__
        sections = track.get_sections()
        print(f"  Track: '{tname}' ({tclass}), {len(sections)} sections")
        if "ControlBoard" in str(tname) or "Control" in str(tname):
            if sections:
                face_section = sections[0]
                face_track = track
                face_binding = binding
                print(f"    *** SELECTED as face section ***")

if not face_section:
    print("\nERROR: No ControlBoard section found."); raise SystemExit

# ── 2. Section info ──
print(f"\n=== FACE SECTION INFO ===")
print(f"Section type: {type(face_section).__name__}")
try:
    print(f"Section range: {face_section.get_start_frame()} to {face_section.get_end_frame()}")
except Exception as e:
    print(f"Section range: error - {e}")

# ── 3. List ALL channels ──
channels = face_section.get_all_channels()
print(f"\n=== ALL CHANNELS ({len(channels)}) ===")

mouth_channels = []
jaw_channels = []
tongue_channels = []
other_channels = []

for ch in channels:
    ch_name = ch.get_name()
    ch_type = type(ch).__name__
    try:
        nkeys = ch.get_num_keys()
    except:
        nkeys = "?"

    line = f"  {ch_name} ({ch_type}) — {nkeys} keys"

    if "mouth" in ch_name.lower():
        mouth_channels.append(line)
    elif "jaw" in ch_name.lower():
        jaw_channels.append(line)
    elif "tongue" in ch_name.lower():
        tongue_channels.append(line)
    else:
        other_channels.append(line)

print(f"\n--- JAW channels ({len(jaw_channels)}) ---")
for c in sorted(jaw_channels):
    print(c)

print(f"\n--- MOUTH channels ({len(mouth_channels)}) ---")
for c in sorted(mouth_channels):
    print(c)

print(f"\n--- TONGUE channels ({len(tongue_channels)}) ---")
for c in sorted(tongue_channels):
    print(c)

print(f"\n--- OTHER channels ({len(other_channels)}) ---")
for c in sorted(other_channels[:50]):  # limit output
    print(c)
if len(other_channels) > 50:
    print(f"  ... and {len(other_channels)-50} more")

# ── 4. Check specific channels for existing keys ──
print(f"\n=== KEY INSPECTION (channels with keys > 0) ===")
for ch in channels:
    try:
        nkeys = ch.get_num_keys()
        if nkeys > 0:
            ch_name = ch.get_name()
            print(f"\n{ch_name}: {nkeys} keys")
            keys = ch.get_keys()
            for k in keys[:20]:  # limit
                frame_val = k.get_time().frame_number.value
                try:
                    val = k.get_value()
                except:
                    val = "?"
                print(f"    tick={frame_val}, value={val}")
            if nkeys > 20:
                print(f"    ... ({nkeys-20} more)")
    except:
        pass

# ── 5. Test keying a value to see if it works ──
print(f"\n=== TEST KEY ===")
test_fn = unreal.FrameNumber(0)
try:
    face_section.add_scalar_parameter_key("CTRL_C_jaw_fwdBack", test_fn, 0.0)
    print("add_scalar_parameter_key('CTRL_C_jaw_fwdBack', 0, 0.0) — OK")
except Exception as e:
    print(f"add_scalar_parameter_key error: {e}")

try:
    face_section.add_vector2d_parameter_key("CTRL_C_jaw", test_fn, unreal.Vector2D(0, 0))
    print("add_vector2d_parameter_key('CTRL_C_jaw', 0, (0,0)) — OK")
except Exception as e:
    print(f"add_vector2d_parameter_key error: {e}")

# Test a potentially wrong name
try:
    face_section.add_scalar_parameter_key("CTRL_L_mouth_lipBiteU", test_fn, 0.0)
    print("add_scalar_parameter_key('CTRL_L_mouth_lipBiteU', 0, 0.0) — OK (name exists)")
except Exception as e:
    print(f"CTRL_L_mouth_lipBiteU error: {e}")

# ── 6. Check tick resolution by reading back ──
print(f"\n=== TICK RESOLUTION CHECK ===")
# Key jaw at tick 800 (should be frame 1 if 800 ticks/frame)
test_fn2 = unreal.FrameNumber(800)
try:
    face_section.add_vector2d_parameter_key("CTRL_C_jaw", test_fn2, unreal.Vector2D(0, -0.99))
    print("Keyed CTRL_C_jaw at tick 800 with Y=-0.99")
except Exception as e:
    print(f"Key at tick 800 error: {e}")

# Now read it back
for ch in channels:
    if "CTRL_C_jaw.Y" in ch.get_name():
        keys = ch.get_keys()
        print(f"CTRL_C_jaw.Y keys after test:")
        for k in keys:
            print(f"  tick={k.get_time().frame_number.value}, val={k.get_value()}")
        break

# Clean up — remove that test key
try:
    face_section.add_vector2d_parameter_key("CTRL_C_jaw", test_fn2, unreal.Vector2D(0, 0))
    print("(cleaned up test key)")
except:
    pass

print("\n=== DEBUG COMPLETE ===")
