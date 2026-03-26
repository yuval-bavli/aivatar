"""Take a viewport screenshot using UE's built-in functionality."""
import unreal

out = []

# Try viewport screenshot
try:
    # Use high-res screenshot
    unreal.AutomationLibrary.take_high_res_screenshot(
        1920, 1080,
        "c:/Users/yuval/src/aivatar/ue_viewport_capture.png"
    )
    out.append("High-res screenshot taken")
except Exception as e:
    out.append(f"High-res failed: {e}")

# Also try editor utility
try:
    result = unreal.EditorLevelLibrary.editor_request_end_play_map()
except:
    pass

# Get viewport info
try:
    subsys = unreal.UnrealEditorSubsystem()
    vp = subsys.get_level_viewport_camera_info()
    out.append(f"Camera location: {vp}")
except Exception as e:
    out.append(f"Camera info: {e}")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("\n".join(out))
