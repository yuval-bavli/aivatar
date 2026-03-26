"""Screenshot key viseme poses by scrubbing to each frame."""
import unreal, time

TICKS_PER_FRAME = 800
OUTPUT_DIR = "c:/Users/yuval/src/aivatar"

visemes = [
    (0, "sil"), (10, "PP"), (20, "FF"), (30, "TH"), (40, "DD"),
    (50, "kk"), (60, "CH"), (70, "SS"), (80, "nn"), (90, "RR"),
    (100, "aa"), (110, "E"), (120, "ih"), (130, "oh"), (140, "ou"),
]

out = []

# Scrub to the "aa" viseme (frame 100) - most dramatic pose for quick visual check
frame = 100
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame * TICKS_PER_FRAME)

# Take a viewport screenshot
try:
    unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, f"{OUTPUT_DIR}/ue_viseme_aa.png")
    out.append(f"Screenshot taken at frame {frame} (aa viseme)")
except Exception as e:
    out.append(f"Screenshot error: {e}")
    # Fallback: try editor utility
    try:
        config = unreal.HighResScreenshotConfig()
        out.append("Trying HighResScreenshotConfig...")
    except:
        out.append("No screenshot method available")

# Also scrub to sil (frame 0) for comparison
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
try:
    unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, f"{OUTPUT_DIR}/ue_viseme_sil.png")
    out.append(f"Screenshot taken at frame 0 (sil viseme)")
except Exception as e:
    out.append(f"sil screenshot error: {e}")

# Scrub to PP (frame 10)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(10 * TICKS_PER_FRAME)
try:
    unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, f"{OUTPUT_DIR}/ue_viseme_pp.png")
    out.append(f"Screenshot taken at frame 10 (PP viseme)")
except Exception as e:
    out.append(f"PP screenshot error: {e}")

# Scrub to oh (frame 130)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(130 * TICKS_PER_FRAME)
try:
    unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, f"{OUTPUT_DIR}/ue_viseme_oh.png")
    out.append(f"Screenshot taken at frame 130 (oh viseme)")
except Exception as e:
    out.append(f"oh screenshot error: {e}")

open(f"{OUTPUT_DIR}/ue_output.txt", "w").write("\n".join(out))
