"""
Test: Use ControlRigSequencerLibrary.set_local_control_rig_float to key controls.
This should go through the proper sequencer keying pipeline.
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

TICKS = 800
lib = unreal.ControlRigSequencerLibrary

# 1. Get the level sequence and find face binding
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# 2. Get control rigs from sequencer
try:
    control_rigs = lib.get_control_rigs(level_seq)
    p(f"Control rigs: {len(control_rigs)}")
    for cr in control_rigs:
        p(f"  {cr.get_name()} ({type(cr).__name__})")
except Exception as e:
    p(f"get_control_rigs error: {e}")
    control_rigs = []

# 3. Try get_visible_control_rigs
try:
    visible = lib.get_visible_control_rigs(level_seq)
    p(f"\nVisible control rigs: {len(visible)}")
    for cr in visible:
        p(f"  {cr.get_name()} ({type(cr).__name__})")
except Exception as e:
    p(f"get_visible_control_rigs error: {e}")

# 4. Check the help/signature for set_local_control_rig_float
p(f"\n=== set_local_control_rig_float signature ===")
try:
    p(help(lib.set_local_control_rig_float))
except Exception as e:
    p(str(e))

p(f"\n=== set_local_control_rig_vector2d signature ===")
try:
    p(help(lib.set_local_control_rig_vector2d))
except Exception as e:
    p(str(e))

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
