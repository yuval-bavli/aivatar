"""
Explore ControlRigSequencerBindingProxy and set_local_control_rig_float signature.
"""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

lib = unreal.ControlRigSequencerLibrary
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

# Get control rig proxies
proxies = lib.get_control_rigs(level_seq)
p(f"Proxies: {len(proxies)}")

for proxy in proxies:
    p(f"\nProxy type: {type(proxy).__name__}")
    # List proxy attributes
    for attr in sorted(dir(proxy)):
        if not attr.startswith('_'):
            p(f"  {attr}")

# Check ControlRigSequencerBindingProxy
p(f"\n=== ControlRigSequencerBindingProxy methods ===")
bp_cls = unreal.ControlRigSequencerBindingProxy
for attr in sorted(dir(bp_cls)):
    if not attr.startswith('_') and callable(getattr(bp_cls, attr, None)):
        p(f"  {attr}()")

# Try accessing proxy properties
for proxy in proxies:
    try:
        cr = proxy.get_editor_property('control_rig')
        p(f"\nControl Rig: {cr.get_name()} ({type(cr).__name__})")
    except Exception as e:
        p(f"Error getting control_rig: {e}")
    try:
        track = proxy.get_editor_property('track')
        p(f"Track: {track.get_display_name()}")
    except Exception as e:
        p(f"Error getting track: {e}")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
