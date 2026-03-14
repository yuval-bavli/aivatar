---
name: unity-screenshot
description: Capture a screenshot of the Unity scene via the agent bridge and display it. Use this whenever you need to see the current state of the avatar in the Unity Editor.
---

# Unity Screenshot — Capturing the Scene

Captures a screenshot of the main camera in Unity via the agent bridge and reads it back so you can see it.

## Steps

1. Use the Python unity_bridge module (preferred):

```python
import sys; sys.path.insert(0, 'unity_3d_model_improver')
import unity_bridge
shot_path = unity_bridge.screenshot()
print(shot_path)
```

Then read the image with the `Read` tool at the returned path.

2. Or via shell (fallback):

```bash
rm -f "unity/aivatar/agent_result.txt"
printf 'screenshot' > "c:/Users/yuval/src/aivatar/unity/aivatar/agent_request.txt"
for i in $(seq 1 50); do
  [ -f "unity/aivatar/agent_result.txt" ] && cat "unity/aivatar/agent_result.txt" && break
  sleep 0.1
done
```

3. Read and display the image with the `Read` tool so you and the user can see it.

## Details

- Screenshots are saved to `unity/aivatar/Assets/Screenshots/` (gitignored).
- Filename format: `screenshot_2026-03-13T21-42-55.png` (ISO 8601, sorts chronologically).
- Images are downscaled to ≤800 px wide, aspect ratio preserved.
- If the result starts with `ERROR:`, report it to the user.
- **Unity must be open** and have registered the bridge watcher (give it focus once after launch if needed).
