"""Add viseme curves to the AnimSequence and load into CR section."""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

FPS = 30.0

VISEMES = [
    (0,   "sil",  {}),
    (10,  "PP",   {"CTRL_C_jaw_openExtreme": 0, "CTRL_L_mouth_pressU": 0.8, "CTRL_R_mouth_pressU": 0.8,
                  "CTRL_L_mouth_pressD": 0.8, "CTRL_R_mouth_pressD": 0.8}),
    (20,  "FF",   {"CTRL_L_mouth_lipsRollD": 0.7, "CTRL_R_mouth_lipsRollD": 0.7,
                  "CTRL_L_mouth_lipBiteU": 0.6, "CTRL_R_mouth_lipBiteU": 0.6}),
    (30,  "TH",   {"CTRL_C_tongue_inOut": 0.8}),
    (40,  "DD",   {"CTRL_C_tongue_press": 0.5, "CTRL_C_tongue_inOut": 0.3}),
    (50,  "kk",   {}),
    (60,  "CH",   {"CTRL_L_mouth_funnelU": 0.6, "CTRL_R_mouth_funnelU": 0.6,
                  "CTRL_L_mouth_funnelD": 0.6, "CTRL_R_mouth_funnelD": 0.6}),
    (70,  "SS",   {"CTRL_L_mouth_stretch": 0.6, "CTRL_R_mouth_stretch": 0.6}),
    (80,  "nn",   {"CTRL_C_tongue_press": 0.4}),
    (90,  "RR",   {"CTRL_L_mouth_funnelU": 0.35, "CTRL_R_mouth_funnelU": 0.35,
                  "CTRL_L_mouth_funnelD": 0.35, "CTRL_R_mouth_funnelD": 0.35}),
    (100, "aa",   {"CTRL_C_jaw_openExtreme": 0.3,
                  "CTRL_L_mouth_lowerLipDepress": 0.6, "CTRL_R_mouth_lowerLipDepress": 0.6,
                  "CTRL_L_mouth_upperLipRaise": 0.4, "CTRL_R_mouth_upperLipRaise": 0.4,
                  "CTRL_L_mouth_stretch": 0.3, "CTRL_R_mouth_stretch": 0.3}),
    (110, "E",    {"CTRL_L_mouth_stretch": 0.45, "CTRL_R_mouth_stretch": 0.45,
                  "CTRL_L_mouth_lowerLipDepress": 0.35, "CTRL_R_mouth_lowerLipDepress": 0.35}),
    (120, "ih",   {"CTRL_L_mouth_stretch": 0.7, "CTRL_R_mouth_stretch": 0.7,
                  "CTRL_L_mouth_cornerPull": 0.35, "CTRL_R_mouth_cornerPull": 0.35}),
    (130, "oh",   {"CTRL_L_mouth_funnelU": 0.7, "CTRL_R_mouth_funnelU": 0.7,
                  "CTRL_L_mouth_funnelD": 0.7, "CTRL_R_mouth_funnelD": 0.7}),
    (140, "ou",   {"CTRL_L_mouth_purseU": 0.7, "CTRL_R_mouth_purseU": 0.7,
                  "CTRL_L_mouth_purseD": 0.7, "CTRL_R_mouth_purseD": 0.7,
                  "CTRL_L_mouth_funnelU": 0.5, "CTRL_R_mouth_funnelU": 0.5}),
]

try:
    # Load existing AnimSequence
    anim_seq = unreal.load_asset("/Game/Aivatar/VisemePoses")
    if not anim_seq:
        p("AnimSequence not found!")
    else:
        p(f"Loaded: {anim_seq.get_name()}")
        anim_lib = unreal.AnimationLibrary

        # Remove any existing curves
        try:
            anim_lib.remove_all_curve_data(anim_seq)
            p("Cleared existing curves")
        except: pass

        # Collect all control names
        all_controls = set()
        for frame, name, controls in VISEMES:
            all_controls.update(controls.keys())

        # Add jaw.Y as a separate control (Vector2D Y component)
        # But AnimSequence curves are just named float curves
        # The Control Rig import should map curve names to control names

        p(f"Adding {len(all_controls)} control curves...")

        for ctrl_name in sorted(all_controls):
            anim_lib.add_curve(anim_seq, ctrl_name,
                             curve_type=unreal.RawCurveTrackTypes.RCT_FLOAT)

            for frame, vis_name, controls in VISEMES:
                time = frame / FPS
                value = controls.get(ctrl_name, 0.0)
                anim_lib.add_float_curve_key(anim_seq, ctrl_name, time, value)

        p(f"Done. Sequence length: {anim_seq.sequence_length}")

        unreal.EditorAssetLibrary.save_asset(anim_seq.get_path_name())
        p("Saved!")

        # Load into CR section
        p("\n=== Loading into CR section ===")
        lib = unreal.ControlRigSequencerLibrary
        level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

        face_track = None
        for binding in level_seq.get_bindings():
            for track in binding.get_tracks():
                if "Face_ControlBoard" in str(track.get_display_name()):
                    face_track = track
                    break
            if face_track: break

        # Clean section first
        for sec in face_track.get_sections():
            face_track.remove_section(sec)
        new_sec = face_track.add_section()
        new_sec.set_start_frame_bounded(False)
        new_sec.set_end_frame_bounded(False)
        p("Fresh section created")

        try:
            lib.load_anim_sequence_into_control_rig_section(new_sec, anim_seq)
            p("load_anim_sequence_into_control_rig_section OK!")
        except Exception as e:
            p(f"load error: {e}")
            p(traceback.format_exc())

        # Check what happened
        channels = new_sec.get_all_channels()
        keyed = 0
        for ch in channels:
            keys = ch.get_keys()
            if len(keys) > 0:
                keyed += 1
                name = ch.get_name()
                if 'jaw' in name.lower() or 'stretch' in name.lower():
                    vals = [(round(k.get_time().frame_number.value/800), round(k.get_value(),3)) for k in keys[:5]]
                    p(f"  {name}: {vals}...")
        p(f"\nTotal keyed: {keyed}/{len(channels)}")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
