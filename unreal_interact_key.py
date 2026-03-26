"""
Try using set_interaction + set_control_rig_world_transform to simulate
user dragging controls, which should key properly.
Also try: set_local_control_rig_floats (plural) which may batch-key.
"""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

TICKS = 800

try:
    lib = unreal.ControlRigSequencerLibrary
    level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

    proxies = lib.get_control_rigs(level_seq)
    cr = None
    proxy = None
    for pr in proxies:
        if 'Face_ControlBoard' in pr.control_rig.get_name():
            cr = pr.control_rig
            proxy = pr
            break

    # Approach 1: Try set_interaction first
    p("=== Approach 1: set_interaction ===")
    try:
        lib.set_interaction(True)
        p("set_interaction(True) OK")
    except Exception as e:
        p(f"set_interaction error: {e}")

    # Move to frame 50
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(50 * TICKS)

    # Try set_local_control_rig_floats (plural - sets multiple at once)
    p("\n=== Approach 2: set_local_control_rig_floats (plural) ===")
    try:
        # Check signature
        lib.set_local_control_rig_floats()
    except Exception as e:
        p(f"Signature hint: {e}")

    try:
        fn50 = unreal.FrameNumber(50 * TICKS)
        lib.set_local_control_rig_floats(
            level_seq, cr,
            ["CTRL_C_jaw_openExtreme"],
            [0.9],
            fn50
        )
        p("set_local_control_rig_floats OK!")
    except Exception as e:
        p(f"Error: {e}")

    # Approach 3: Try set_control_rig_world_transform
    p("\n=== Approach 3: set_control_rig_world_transform ===")
    try:
        lib.set_control_rig_world_transform()
    except Exception as e:
        p(f"Signature hint: {e}")

    # Approach 4: Use the section's add_scalar_parameter_key but on the _0 channels
    p("\n=== Approach 4: Check existing channel names ===")
    face_track = None
    for binding in level_seq.get_bindings():
        for track in binding.get_tracks():
            if "Face_ControlBoard" in str(track.get_display_name()):
                face_track = track
                break
        if face_track: break

    sec = face_track.get_sections()[0]

    # List ALL jaw channel names with their exact suffix
    p("All jaw channels in section:")
    for ch in sec.get_all_channels():
        name = ch.get_name()
        if 'jaw' in name.lower():
            keys = ch.get_keys()
            p(f"  {name} ({len(keys)} keys)")

    # Approach 5: Try get_channel by name
    p("\n=== Approach 5: get_channel ===")
    try:
        ch = sec.get_channel("CTRL_C_jaw_openExtreme")
        p(f"get_channel result: {ch}")
    except Exception as e:
        p(f"get_channel error: {e}")

    # Approach 6: Try keying on _5 channel directly (the original one)
    p("\n=== Approach 6: Key on _5 channel directly ===")
    for ch in sec.get_all_channels():
        if ch.get_name() == "CTRL_C_jaw_openExtreme_5":
            fn0 = unreal.FrameNumber(0)
            fn50 = unreal.FrameNumber(50 * TICKS)
            fn100 = unreal.FrameNumber(100 * TICKS)
            ch.add_key(fn0, 0.0)
            ch.add_key(fn50, 0.9)
            ch.add_key(fn100, 0.0)
            keys = ch.get_keys()
            p(f"  Keyed _5 channel: {len(keys)} keys")
            for k in keys:
                p(f"    tick={k.get_time().frame_number.value} val={k.get_value()}")
            break

    lib.set_interaction(False)

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
