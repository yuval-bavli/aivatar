"""Capture viewport at current frame using UE high-res screenshot."""
import unreal
unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, "viseme_check.png")
open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write("Screenshot taken")
