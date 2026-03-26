"""Boost tongue visibility for TH viseme (frame 30)."""
import unreal, io

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
face_section = None
for binding in level_seq.get_bindings():
    for track in binding.get_tracks():
        if "Face_ControlBoard" in str(track.get_display_name()):
            sections = track.get_sections()
            if sections:
                face_section = sections[0]
                break
    if face_section: break

TICKS_PER_FRAME = 800

def key_scalar(name, frame, value):
    fn = unreal.FrameNumber(frame * TICKS_PER_FRAME)
    face_section.add_scalar_parameter_key(name, fn, float(value))

def key_vector2d(name, frame, x, y):
    fn = unreal.FrameNumber(frame * TICKS_PER_FRAME)
    face_section.add_vector2d_parameter_key(name, fn, unreal.Vector2D(x, y))

# Frame 30 = TH: boost tongue protrusion and open mouth a bit more
frame = 30
key_scalar("CTRL_C_tongue_inOut", frame, 0.8)       # was 0.4 — much more visible
key_vector2d("CTRL_C_tongue_tipMove", frame, 0, 0.3) # tip up toward teeth
key_vector2d("CTRL_C_jaw", frame, 0, -0.35)          # was -0.25 — open more

# Also for DD (frame 40): tongue pressed against alveolar ridge
frame = 40
key_scalar("CTRL_C_tongue_inOut", frame, 0.3)        # slight protrusion
key_vector2d("CTRL_C_tongue_tipMove", frame, 0, 0.4) # tip up against upper teeth

# For nn (frame 80): tongue tip up
frame = 80
key_scalar("CTRL_C_tongue_inOut", frame, 0.2)
key_vector2d("CTRL_C_tongue_tipMove", frame, 0, 0.3)

p("Tongue boosted for TH (frame 30), DD (frame 40), nn (frame 80)")

# Verify
for ch in face_section.get_all_channels():
    if "tongue_inOut" in ch.get_name():
        keys = ch.get_keys()
        p(f"\n{ch.get_name()}: {len(keys)} keys")
        for k in keys:
            fv = k.get_time().frame_number.value
            val = k.get_value()
            if val != 0:
                p(f"  frame={fv}, val={val:.2f}")
        break

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
