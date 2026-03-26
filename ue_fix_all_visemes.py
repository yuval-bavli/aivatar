import unreal
import io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

# 1. Get Sequence and Face Rig
level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
if not level_seq:
    p("ERROR: No Level Sequence open")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
    raise SystemExit

lib = unreal.ControlRigSequencerLibrary
rigs = lib.get_control_rigs(level_seq)
face_rig = None
for proxy in rigs:
    cr = proxy.control_rig
    if "Face" in cr.get_name():
        face_rig = cr
        break

if not face_rig:
    p("ERROR: Face_ControlBoard_CtrlRig not found")
    open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
    raise SystemExit

face_section = None
for b in level_seq.get_bindings():
    for t in b.get_tracks():
        if "Face_ControlBoard" in str(t.get_display_name()):
            face_section = t.get_sections()[0]
            break
    if face_section:
        break

TICKS = 800
TR = unreal.MovieSceneTimeUnit.TICK_RESOLUTION

# Define Jaw Y positive values (mouth opening amount)
# Higher positive means wider open mouth
JAW_Y_VALUES = {
    "sil": 0.0,
    "PP": 0.0,     # Lips pressed, standard
    "FF": 0.1,     # Slight open, lower lip to teeth
    "TH": 0.15,    # Tongue between teeth
    "DD": 0.2,     # Jaw open slightly for tongue behind teeth
    "kk": 0.2,     # Back tongue
    "CH": 0.15,    # Rounded lips open
    "SS": 0.08,    # Teeth nearly closed but open enough
    "nn": 0.15,    # Jaw open slightly for tongue up
    "RR": 0.15,    # Slightly rounded
    "aa": 0.5,     # Wide open
    "E":  0.3,     # Mid open
    "ih": 0.15,    # Narrow open
    "oh": 0.35,    # Round open
    "ou": 0.2      # Tight pucker
}
# Define extra custom tongue features
TONGUE_INOUT = {
    "TH": -0.2, # sticking out
}

VISEMES = [
    (0, "sil"), (10, "PP"), (20, "FF"), (30, "TH"), (40, "DD"),
    (50, "kk"), (60, "CH"), (70, "SS"), (80, "nn"), (90, "RR"),
    (100, "aa"), (110, "E"), (120, "ih"), (130, "oh"), (140, "ou"),
]

p("Setting Scalar overrides and Dummy Vector2D keys...")

# Set up dummy vector keys (which UE sets to 0,0 anyway) and any specific scalar overrides
for frame, name in VISEMES:
    fn = unreal.FrameNumber(frame * TICKS)
    # Set Vector2D dummy values
    lib.set_local_control_rig_vector2d(level_seq, face_rig, "CTRL_C_jaw",
        fn, unreal.Vector2D(0, 0), time_unit=TR, set_key=True)
    lib.set_local_control_rig_vector2d(level_seq, face_rig, "CTRL_C_tongue_tipMove",
        fn, unreal.Vector2D(0, 0), time_unit=TR, set_key=True)
    
    # Specific tongue values depending on viseme
    tongue_inout_val = TONGUE_INOUT.get(name, 0.0)
    lib.set_local_control_rig_float(level_seq, face_rig, "CTRL_C_tongue_inOut", 
        fn, tongue_inout_val, time_unit=TR, set_key=True)
        
    if name == "nn" or name == "DD":
        # Keep tongue press strong enough for "LA" type sounds
        lib.set_local_control_rig_float(level_seq, face_rig, "CTRL_C_tongue_press", 
            fn, 0.5, time_unit=TR, set_key=True)

# Important: Patch Vector2D values on channels because of UE bug
p("\nPatching Vector2D Channels (Jaw.Y and Tongue_tipMove.Y)...")

patched_count = 0
for ch in face_section.get_all_channels():
    full_name = ch.get_name()
    if "CTRL_C_jaw.Y" in full_name:
        for k in ch.get_keys():
            frame_idx = k.get_time().frame_number.value
            # Find viseme name
            v_name = next((v for f, v in VISEMES if f == frame_idx), None)
            if v_name:
                val = JAW_Y_VALUES.get(v_name, 0.0)
                k.set_value(val)
                patched_count += 1
    
    elif "CTRL_C_tongue_tipMove.Y" in full_name:
        # Give tongue a lift for nn and DD
        for k in ch.get_keys():
            frame_idx = k.get_time().frame_number.value
            v_name = next((v for f, v in VISEMES if f == frame_idx), None)
            
            if v_name in ["nn", "DD"]:
                k.set_value(0.2) # Try positive 0.2 for tongue Up lift
                patched_count += 1
            else:
                k.set_value(0.0)

p(f"Patched {patched_count} channel keys across the timeline.")

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
