"""Try setting control rig values directly, bypassing channel approach."""
import unreal

out = []
lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

rigs = lib.get_control_rigs(level_seq)
face_rig = None
for proxy in rigs:
    cr = proxy.control_rig
    if "Face" in cr.get_name():
        face_rig = cr
        break

out.append(f"Face rig: {face_rig.get_name()}")

# List available control rig methods
rig_methods = [m for m in dir(face_rig) if not m.startswith('_')]
set_methods = [m for m in rig_methods if 'set' in m.lower() and ('value' in m.lower() or 'control' in m.lower() or 'float' in m.lower())]
out.append(f"Set methods: {set_methods}")

get_methods = [m for m in rig_methods if 'get' in m.lower() and ('value' in m.lower() or 'control' in m.lower() or 'float' in m.lower())]
out.append(f"Get methods: {get_methods}")

# Check for autokey and key methods on the rig
key_methods = [m for m in rig_methods if 'key' in m.lower() or 'auto' in m.lower()]
out.append(f"Key/Auto methods: {key_methods}")

# Check ControlRigSequencerLibrary methods
lib_methods = [m for m in dir(lib) if not m.startswith('_') and ('key' in m.lower() or 'set' in m.lower() or 'local' in m.lower())]
out.append(f"\nLib set/key methods: {lib_methods}")

# Try getting current value of jaw control
try:
    val = face_rig.get_control_value("CTRL_C_jaw")
    out.append(f"\nget_control_value(jaw): {val}")
except Exception as e:
    out.append(f"\nget_control_value failed: {e}")

# Try finding value setter
try:
    face_rig.set_control_value("CTRL_C_jaw", unreal.Vector2D(0, -1.0))
    out.append("set_control_value(jaw, Vector2D(0,-1)): OK")
except Exception as e:
    out.append(f"set_control_value failed: {e}")

# Try with RigControlValue
try:
    controls = face_rig.available_controls()
    out.append(f"\navailable_controls count: {len(controls)}")
    jaw_ctrls = [c for c in controls if 'jaw' in c.lower()]
    out.append(f"Jaw controls: {jaw_ctrls}")
except Exception as e:
    out.append(f"available_controls: {e}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
