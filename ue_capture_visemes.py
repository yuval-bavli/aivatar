"""Scrub to key visemes and capture viewport screenshots."""
import unreal, subprocess, time, os

TICKS_PER_FRAME = 800
OUTPUT_DIR = "c:/Users/yuval/src/aivatar"

# Key visemes to check
checks = [(0, "sil"), (10, "PP"), (100, "aa"), (130, "oh"), (140, "ou")]

out = []

for frame, name in checks:
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS_PER_FRAME)
    # Force viewport refresh
    unreal.EditorLevelLibrary.get_editor_world()

    # Use HighResScreenshot command
    fname = f"viseme_{name}"
    screenshot_path = f"{OUTPUT_DIR}/ue_viseme_{name}.png"

    # Use the screenshot request
    unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, fname)
    out.append(f"Frame {frame}: {name} - screenshot requested as {fname}")

open(f"{OUTPUT_DIR}/ue_output.txt", "w").write("\n".join(out))
