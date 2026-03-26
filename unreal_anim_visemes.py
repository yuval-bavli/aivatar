"""
Create an AnimSequence with viseme control curves, then load it
into the face Control Rig section.
"""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

FPS = 30
FRAME_DURATION = 10  # frames between visemes
NUM_VISEMES = 15
TOTAL_FRAMES = NUM_VISEMES * FRAME_DURATION  # 150 frames = 5 seconds

try:
    # Step 1: Create AnimSequence asset
    p("=== Creating AnimSequence ===")

    # Get the face skeleton
    face_skel = unreal.load_asset("/Game/MetaHumans/model4/Face/SKM_model4_FaceMesh_Skeleton")
    if not face_skel:
        # Try to find it
        assets = unreal.EditorAssetLibrary.list_assets("/Game/MetaHumans/model4/Face/", recursive=False)
        for a in assets:
            if 'Skeleton' in a:
                p(f"  Found: {a}")
        face_skel = unreal.load_asset("/Game/MetaHumans/model4/Face/SKM_model4_FaceMesh")
        if face_skel:
            p(f"  Loaded mesh: {type(face_skel).__name__}")

    # Create the package and anim sequence
    factory = unreal.AnimSequenceFactory()
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    anim_seq = asset_tools.create_asset(
        "VisemePoses", "/Game/MetaHumans/model4/Face",
        unreal.AnimSequence, factory
    )

    if not anim_seq:
        p("Failed to create AnimSequence, trying alternate path")
        anim_seq = asset_tools.create_asset(
            "VisemePoses", "/Game/Aivatar",
            unreal.AnimSequence, factory
        )

    if anim_seq:
        p(f"Created: {anim_seq.get_name()} ({type(anim_seq).__name__})")

        # Set duration
        total_seconds = TOTAL_FRAMES / FPS
        anim_seq.set_editor_property('sequence_length', total_seconds)
        p(f"Duration: {total_seconds}s ({TOTAL_FRAMES} frames)")

        anim_lib = unreal.AnimationLibrary

        # Add curves for each control
        # Viseme definitions: (frame, name, controls_dict)
        VISEMES = [
            (0,   "sil",  {}),
            (10,  "PP",   {"CTRL_C_jaw.Y": -0.05, "CTRL_L_mouth_pressU": 0.8, "CTRL_R_mouth_pressU": 0.8,
                          "CTRL_L_mouth_pressD": 0.8, "CTRL_R_mouth_pressD": 0.8}),
            (20,  "FF",   {"CTRL_C_jaw.Y": -0.15, "CTRL_L_mouth_lipsRollD": 0.7, "CTRL_R_mouth_lipsRollD": 0.7,
                          "CTRL_L_mouth_lipBiteU": 0.6, "CTRL_R_mouth_lipBiteU": 0.6}),
            (30,  "TH",   {"CTRL_C_jaw.Y": -0.35, "CTRL_C_tongue_inOut": 0.8}),
            (40,  "DD",   {"CTRL_C_jaw.Y": -0.35, "CTRL_C_tongue_press": 0.5, "CTRL_C_tongue_inOut": 0.3}),
            (50,  "kk",   {"CTRL_C_jaw.Y": -0.3}),
            (60,  "CH",   {"CTRL_C_jaw.Y": -0.15, "CTRL_L_mouth_funnelU": 0.6, "CTRL_R_mouth_funnelU": 0.6,
                          "CTRL_L_mouth_funnelD": 0.6, "CTRL_R_mouth_funnelD": 0.6}),
            (70,  "SS",   {"CTRL_C_jaw.Y": -0.08, "CTRL_L_mouth_stretch": 0.6, "CTRL_R_mouth_stretch": 0.6}),
            (80,  "nn",   {"CTRL_C_jaw.Y": -0.15, "CTRL_C_tongue_press": 0.4}),
            (90,  "RR",   {"CTRL_C_jaw.Y": -0.2, "CTRL_L_mouth_funnelU": 0.35, "CTRL_R_mouth_funnelU": 0.35,
                          "CTRL_L_mouth_funnelD": 0.35, "CTRL_R_mouth_funnelD": 0.35}),
            (100, "aa",   {"CTRL_C_jaw.Y": -0.7, "CTRL_C_jaw_openExtreme": 0.3,
                          "CTRL_L_mouth_lowerLipDepress": 0.6, "CTRL_R_mouth_lowerLipDepress": 0.6,
                          "CTRL_L_mouth_upperLipRaise": 0.4, "CTRL_R_mouth_upperLipRaise": 0.4,
                          "CTRL_L_mouth_stretch": 0.3, "CTRL_R_mouth_stretch": 0.3}),
            (110, "E",    {"CTRL_C_jaw.Y": -0.4, "CTRL_L_mouth_stretch": 0.45, "CTRL_R_mouth_stretch": 0.45,
                          "CTRL_L_mouth_lowerLipDepress": 0.35, "CTRL_R_mouth_lowerLipDepress": 0.35}),
            (120, "ih",   {"CTRL_C_jaw.Y": -0.15, "CTRL_L_mouth_stretch": 0.7, "CTRL_R_mouth_stretch": 0.7,
                          "CTRL_L_mouth_cornerPull": 0.35, "CTRL_R_mouth_cornerPull": 0.35}),
            (130, "oh",   {"CTRL_C_jaw.Y": -0.4, "CTRL_L_mouth_funnelU": 0.7, "CTRL_R_mouth_funnelU": 0.7,
                          "CTRL_L_mouth_funnelD": 0.7, "CTRL_R_mouth_funnelD": 0.7}),
            (140, "ou",   {"CTRL_C_jaw.Y": -0.15, "CTRL_L_mouth_purseU": 0.7, "CTRL_R_mouth_purseU": 0.7,
                          "CTRL_L_mouth_purseD": 0.7, "CTRL_R_mouth_purseD": 0.7,
                          "CTRL_L_mouth_funnelU": 0.5, "CTRL_R_mouth_funnelU": 0.5}),
        ]

        # Collect all unique control names
        all_controls = set()
        for frame, name, controls in VISEMES:
            all_controls.update(controls.keys())
        p(f"Unique controls: {len(all_controls)}")

        # Add curves for each control
        for ctrl_name in sorted(all_controls):
            try:
                anim_lib.add_curve(anim_seq, ctrl_name, curve_type=unreal.RawCurveTrackTypes.RCT_FLOAT)
            except Exception as e:
                p(f"  add_curve({ctrl_name}) error: {e}")
                continue

            # Add keys for each viseme frame
            for frame, vis_name, controls in VISEMES:
                time = frame / FPS
                value = controls.get(ctrl_name, 0.0)
                try:
                    anim_lib.add_float_curve_key(anim_seq, ctrl_name, time, value)
                except Exception as e:
                    p(f"  add_key({ctrl_name}, {time}, {value}) error: {e}")
                    break

        p(f"Added curves and keys")

        # Save
        unreal.EditorAssetLibrary.save_asset(anim_seq.get_path_name())
        p(f"Saved: {anim_seq.get_path_name()}")

        # Step 2: Load into Control Rig section
        p("\n=== Loading into Control Rig section ===")
        lib = unreal.ControlRigSequencerLibrary
        level_seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()

        face_track = None
        for binding in level_seq.get_bindings():
            for track in binding.get_tracks():
                if "Face_ControlBoard" in str(track.get_display_name()):
                    face_track = track
                    break
            if face_track: break

        sec = face_track.get_sections()[0]

        try:
            lib.load_anim_sequence_into_control_rig_section(sec, anim_seq)
            p("load_anim_sequence_into_control_rig_section OK!")
        except Exception as e:
            p(f"load error: {e}")
            p(traceback.format_exc())

        # Check keyed channels
        channels = sec.get_all_channels()
        keyed = 0
        for ch in channels:
            keys = ch.get_keys()
            if len(keys) > 0:
                keyed += 1
        p(f"Keyed channels: {keyed}/{len(channels)}")

    else:
        p("Failed to create AnimSequence!")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
