"""
Test: Key jaw open using ControlRigSequencerLibrary.set_local_control_rig_float.
This should properly key the Control Rig through the sequencer pipeline.
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

TICKS = 800
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# Get Face_ControlBoard proxy
proxies = lib.get_control_rigs(level_seq)
face_proxy = None
for proxy in proxies:
    cr = proxy.control_rig
    if 'Face_ControlBoard' in cr.get_name():
        face_proxy = proxy
        p(f"Found Face proxy: {cr.get_name()}")
        break

if not face_proxy:
    p("ERROR: Face_ControlBoard not found")
else:
    cr = face_proxy.control_rig

    # List available controls on the rig
    hierarchy = cr.get_hierarchy()
    p(f"\nHierarchy type: {type(hierarchy).__name__}")

    # Check hierarchy methods
    for attr in sorted(dir(hierarchy)):
        if not attr.startswith('_') and ('control' in attr.lower() or 'key' in attr.lower() or 'element' in attr.lower()):
            p(f"  hierarchy.{attr}")

    # Try to get control names
    try:
        # RigHierarchy methods for getting controls
        controls = []
        for attr in dir(hierarchy):
            if 'get_all' in attr.lower() or 'get_control' in attr.lower():
                p(f"\n  Trying hierarchy.{attr}()...")
                try:
                    result = getattr(hierarchy, attr)()
                    if result:
                        p(f"    Returned {len(result)} items")
                        if len(result) > 0:
                            p(f"    First: {result[0]} ({type(result[0]).__name__})")
                            if len(result) > 1:
                                p(f"    Second: {result[1]}")
                except Exception as e:
                    p(f"    Error: {e}")
    except Exception as e:
        p(f"Error exploring hierarchy: {e}")

    # Try set_local_control_rig_float - key jaw open at frame 50
    p("\n=== Attempting to key jaw ===")
    try:
        # set_local_control_rig_float(level_sequence, control_rig, control_name, frame, value, time_unit, set_key)
        # Try different call signatures
        fn50 = unreal.FrameNumber(50 * TICKS)

        # Attempt 1: with proxy
        lib.set_local_control_rig_float(
            level_seq,
            face_proxy.control_rig,
            "CTRL_C_jaw_openExtreme",
            0.8,
            fn50
        )
        p("set_local_control_rig_float OK!")
    except Exception as e:
        p(f"Attempt 1 error: {e}")

    try:
        # Attempt 2: different arg order
        lib.set_local_control_rig_float(
            level_seq,
            face_proxy.control_rig,
            "CTRL_C_jaw_openExtreme",
            fn50,
            0.8
        )
        p("Attempt 2 OK!")
    except Exception as e:
        p(f"Attempt 2 error: {e}")

    try:
        # Attempt 3: keyword args
        lib.set_local_control_rig_float(
            level_sequence=level_seq,
            control_rig=face_proxy.control_rig,
            control_name="CTRL_C_jaw_openExtreme",
            value=0.8,
            time=fn50,
            set_key=True
        )
        p("Attempt 3 OK!")
    except Exception as e:
        p(f"Attempt 3 error: {e}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
