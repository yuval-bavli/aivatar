"""Find the right skeleton, create AnimSequence with it."""
import unreal, io, traceback

out = io.StringIO()
def p(msg=""): out.write(str(msg) + "\n")

try:
    # Find the face skeleton asset
    p("=== Looking for Face skeleton ===")
    assets = unreal.EditorAssetLibrary.list_assets("/Game/MetaHumans/model4/Face/", recursive=False)
    for a in assets:
        p(f"  {a}")

    # Try loading the skeletal mesh to get its skeleton
    face_mesh = unreal.load_asset("/Game/MetaHumans/model4/Face/SKM_model4_FaceMesh")
    if face_mesh:
        p(f"\nFace mesh: {face_mesh.get_name()} ({type(face_mesh).__name__})")
        skel = face_mesh.get_editor_property('skeleton')
        if skel:
            p(f"Skeleton: {skel.get_name()} ({skel.get_path_name()})")
        else:
            p("No skeleton property")

    # Also check common MetaHuman skeleton locations
    p("\n=== Common skeleton paths ===")
    for path in ["/Game/MetaHumans/Common/Face/", "/Game/MetaHumans/Common/"]:
        try:
            assets2 = unreal.EditorAssetLibrary.list_assets(path, recursive=False)
            for a in assets2:
                if 'skeleton' in a.lower() or 'skel' in a.lower():
                    p(f"  {a}")
        except:
            pass

    # Create AnimSequence with skeleton
    if skel:
        p(f"\n=== Creating AnimSequence with skeleton ===")
        factory = unreal.AnimSequenceFactory()
        factory.set_editor_property('target_skeleton', skel)

        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        anim_seq = asset_tools.create_asset(
            "VisemePoses", "/Game/Aivatar",
            unreal.AnimSequence, factory
        )
        if anim_seq:
            p(f"Created: {anim_seq.get_path_name()}")

            # Set number of frames and duration
            FPS = 30
            TOTAL_FRAMES = 150
            total_seconds = TOTAL_FRAMES / FPS

            # Use set_editor_property to set various properties
            try:
                # Try different ways to set length
                for attr in dir(anim_seq):
                    if 'length' in attr.lower() or 'frame' in attr.lower() or 'duration' in attr.lower():
                        if not attr.startswith('_') and not callable(getattr(anim_seq, attr, None)):
                            p(f"  anim_seq.{attr}")
            except: pass

            anim_seq.set_editor_property('sequence_length', total_seconds)
            p(f"Set duration to {total_seconds}s")

            # Add a test curve
            anim_lib = unreal.AnimationLibrary
            anim_lib.add_curve(anim_seq, "CTRL_C_jaw_openExtreme",
                             curve_type=unreal.RawCurveTrackTypes.RCT_FLOAT)
            anim_lib.add_float_curve_key(anim_seq, "CTRL_C_jaw_openExtreme", 0.0, 0.0)
            anim_lib.add_float_curve_key(anim_seq, "CTRL_C_jaw_openExtreme", 50.0/FPS, 0.8)
            anim_lib.add_float_curve_key(anim_seq, "CTRL_C_jaw_openExtreme", 100.0/FPS, 0.0)
            p("Added test curve: jaw_openExtreme")

            unreal.EditorAssetLibrary.save_asset(anim_seq.get_path_name())
            p("Saved!")

            # Now load into control rig section
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

            sec = face_track.get_sections()[0]
            try:
                lib.load_anim_sequence_into_control_rig_section(sec, anim_seq)
                p("load_anim_sequence_into_control_rig_section OK!")
            except Exception as e:
                p(f"load error: {e}")

            # Check results
            keyed = 0
            for ch in sec.get_all_channels():
                keys = ch.get_keys()
                if len(keys) > 0:
                    keyed += 1
                    name = ch.get_name()
                    if 'jaw' in name.lower():
                        vals = [(round(k.get_time().frame_number.value/800), round(k.get_value(),3)) for k in keys[:5]]
                        p(f"  {name}: {vals}")
            p(f"Total keyed: {keyed}")

        else:
            p("Failed to create AnimSequence")

except Exception as e:
    p(f"ERROR: {e}")
    p(traceback.format_exc())

p("\n=== DONE ===")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(out.getvalue())
