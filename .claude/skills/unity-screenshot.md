# Unity Screenshot — Capturing Without the UI

To see the current state of the Unity scene, capture a screenshot of the main camera using the agent bridge (see `unity-run.md` for the full protocol).

## Steps

1. Read `unity-run.md` if you haven't already — it explains the bridge.
2. Run the capture:

```bash
rm -f "unity/aivatar/agent_result.txt"
echo screenshot > "unity/aivatar/agent_request.txt"
for i in $(seq 1 50); do
  [ -f "unity/aivatar/agent_result.txt" ] && cat "unity/aivatar/agent_result.txt" && break
  sleep 0.1
done
```

3. Read the result file path and display the image with the `Read` tool so you and the user can see it.

## Details

- Screenshots are saved to `unity/aivatar/Assets/Screenshots/` (gitignored).
- Filename format: `screenshot_2026-03-13T21-42-55.png` (ISO 8601, sorts chronologically).
- Images are downscaled to ≤800 px wide, aspect ratio preserved.
- If the result starts with `ERROR:`, report it to the user.
