"""Capture screenshots of key visemes for verification."""
import unreal

TICKS = 800
viseme_frames = [
    (0, "sil"), (10, "PP"), (30, "TH"), (50, "kk"),
    (100, "aa"), (110, "E"), (130, "oh"), (140, "ou")
]

for frame, name in viseme_frames:
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS)
    unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, f"viseme_{name}.png")

open("c:/Users/yuval/src/aivatar/ue_output.txt", "w").write(
    f"Captured {len(viseme_frames)} viseme screenshots")
