"""
Verify the key was placed, then test jaw.Y (Vector2D control).
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

TICKS = 800
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# Get Face proxy
proxies = lib.get_control_rigs(level_seq)
face_proxy = None
for proxy in proxies:
    cr = proxy.control_rig
    if 'Face_ControlBoard' in cr.get_name():
        face_proxy = proxy
        break

cr = face_proxy.control_rig

# Check what was keyed
face_track = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            face_track = track
            break
    if face_track: break

section = face_track.get_sections()[0]
channels = section.get_all_channels()
keyed_channels = []
for ch in channels:
    try:
        keys = ch.get_keys()
        if len(keys) > 0:
            keyed_channels.append((ch.get_name(), len(keys)))
    except:
        pass
p(f"Keyed channels after test: {keyed_channels}")

# Now test Vector2D control (CTRL_C_jaw is a 2D control: X=left/right, Y=open/close)
p("\n=== Testing set_local_control_rig_vector2d ===")
try:
    fn0 = unreal.FrameNumber(0)
    fn50 = unreal.FrameNumber(50 * TICKS)

    # Key jaw at rest (frame 0)
    lib.set_local_control_rig_vector2d(
        level_seq, cr, "CTRL_C_jaw",
        fn0, unreal.Vector2D(0, 0)
    )
    p("Frame 0: jaw (0,0) OK")

    # Key jaw wide open (frame 50)
    lib.set_local_control_rig_vector2d(
        level_seq, cr, "CTRL_C_jaw",
        fn50, unreal.Vector2D(0, -0.7)
    )
    p("Frame 50: jaw (0,-0.7) OK")

    # Also key jaw_openExtreme at frame 50
    lib.set_local_control_rig_float(
        level_seq, cr, "CTRL_C_jaw_openExtreme",
        fn50, 0.5
    )
    p("Frame 50: jaw_openExtreme 0.5 OK")

    # Key back to rest at frame 100
    lib.set_local_control_rig_vector2d(
        level_seq, cr, "CTRL_C_jaw",
        unreal.FrameNumber(100 * TICKS), unreal.Vector2D(0, 0)
    )
    lib.set_local_control_rig_float(
        level_seq, cr, "CTRL_C_jaw_openExtreme",
        unreal.FrameNumber(100 * TICKS), 0.0
    )
    p("Frame 100: back to rest OK")

except Exception as e:
    p(f"Error: {e}")
    import traceback
    p(traceback.format_exc())

# Verify keys
channels = section.get_all_channels()
p(f"\n=== Final keyed channels ===")
for ch in channels:
    try:
        keys = ch.get_keys()
        if len(keys) > 0:
            name = ch.get_name()
            p(f"  {name}: {len(keys)} keys")
            for k in keys:
                tick = k.get_time().frame_number.value
                val = k.get_value()
                p(f"    tick={tick} ({tick//TICKS}f) val={val}")
    except:
        pass

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
