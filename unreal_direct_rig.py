"""
Direct approach: set control values on the rig hierarchy itself.
Skip sequencer entirely - just move the jaw to confirm the rig works.
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# Get Face ControlRig
proxies = lib.get_control_rigs(level_seq)
cr = None
for proxy in proxies:
    if 'Face_ControlBoard' in proxy.control_rig.get_name():
        cr = proxy.control_rig
        break

hierarchy = cr.get_hierarchy()

# List jaw controls
p("=== Jaw/mouth controls ===")
controls = hierarchy.get_controls()
jaw_controls = [c for c in controls if 'jaw' in c.name.lower()]
for c in jaw_controls:
    p(f"  {c.name} (type={c.type})")
    # Read current value
    try:
        val = hierarchy.get_control_value(c, 'current')
        p(f"    current value: {val}")
    except Exception as e:
        p(f"    get_control_value error: {e}")

# Try to set CTRL_C_jaw value directly
p("\n=== Setting jaw value directly ===")
jaw_key = unreal.RigElementKey(name="CTRL_C_jaw", type=unreal.RigElementType.CONTROL)

# Read current value
try:
    cur = hierarchy.get_control_value(jaw_key, 'current')
    p(f"Current jaw value: {cur}")
except Exception as e:
    p(f"Read error: {e}")

# Try Vector2D approach
try:
    v2d = unreal.Vector2D(0, -0.9)
    cv = hierarchy.make_control_value_from_vector2d(v2d)
    hierarchy.set_control_value(jaw_key, cv, value_type='current')
    p(f"set_control_value(jaw, Vector2D(0,-0.9)) OK!")
except Exception as e:
    p(f"Vector2D set error: {e}")
    import traceback
    p(traceback.format_exc())

# Try float approach on jaw_openExtreme
p("\n=== Setting jaw_openExtreme directly ===")
oe_key = unreal.RigElementKey(name="CTRL_C_jaw_openExtreme", type=unreal.RigElementType.CONTROL)
try:
    cv = hierarchy.make_control_value_from_float(0.8)
    hierarchy.set_control_value(oe_key, cv, value_type='current')
    p(f"set_control_value(jaw_openExtreme, 0.8) OK!")
except Exception as e:
    p(f"Float set error: {e}")
    import traceback
    p(traceback.format_exc())

# Read back
try:
    cur = hierarchy.get_control_value(jaw_key, 'current')
    p(f"\nJaw value after set: {cur}")
    v2d_back = hierarchy.get_vector2d_from_control_value(cur)
    p(f"  As Vector2D: {v2d_back}")
except Exception as e:
    p(f"Read back error: {e}")

p("\n=== DONE - Check viewport! ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
