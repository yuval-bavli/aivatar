"""
Create an AnimSequence with viseme control curves, then load it
into the Control Rig section using the import pipeline.
"""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    # Check AnimSequence creation
    p("=== AnimSequence creation ===")

    # Check if AnimationLibrary exists
    try:
        anim_lib = unreal.AnimationLibrary
        for attr in sorted(dir(anim_lib)):
            if not attr.startswith('_') and ('curve' in attr.lower() or 'add' in attr.lower()
                or 'create' in attr.lower() or 'key' in attr.lower()):
                p(f"  AnimationLibrary.{attr}")
    except Exception as e:
        p(f"AnimationLibrary error: {e}")

    # Check load_anim_sequence_into_control_rig_section signature
    p("\n=== load_anim_sequence_into_control_rig_section ===")
    lib = unreal.ControlRigSequencerLibrary
    try:
        lib.load_anim_sequence_into_control_rig_section()
    except Exception as e:
        p(str(e))

    # Check MovieSceneUserImportFBXControlRigSettings
    p("\n=== import_fbx_to_control_rig_track ===")
    try:
        lib.import_fbx_to_control_rig_track()
    except Exception as e:
        p(str(e))

    # Check FBX import settings
    p("\n=== MovieSceneUserImportFBXControlRigSettings ===")
    settings = unreal.MovieSceneUserImportFBXControlRigSettings()
    for attr in sorted(dir(settings)):
        if not attr.startswith('_') and not attr.startswith('get_') and not attr.startswith('set_'):
            try:
                val = getattr(settings, attr)
                if not callable(val):
                    p(f"  {attr} = {val}")
            except:
                pass

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
