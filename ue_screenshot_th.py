"""Take a large close-up screenshot of frame 30 (TH viseme) to verify teeth opening."""
import json, urllib.request, time
import win32gui, win32con
from PIL import ImageGrab, Image, ImageDraw

UE_API = "http://127.0.0.1:30010/remote/object/call"
def ue_exec(code):
    payload = json.dumps({
        "objectPath": "/Script/PythonScriptPlugin.Default__PythonScriptLibrary",
        "functionName": "ExecutePythonCommand",
        "parameters": {"PythonCommand": code}
    }).encode()
    req = urllib.request.Request(UE_API, data=payload,
        headers={"Content-Type": "application/json"}, method="PUT")
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())

results = []
def callback(hwnd, extra):
    title = win32gui.GetWindowText(hwnd)
    if 'Unreal Editor' in title and win32gui.IsWindowVisible(hwnd):
        results.append((hwnd, title))
win32gui.EnumWindows(callback, None)
hwnd = results[0][0]
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
time.sleep(1)

# Scrub to frame 30 (TH) using correct display-rate frame number
ue_exec("import unreal; unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30)")
time.sleep(0.8)

# Capture the viewport area - larger crop for better visibility
rect = win32gui.GetWindowRect(hwnd)
x, y, x2, y2 = rect
w, h = x2 - x, y2 - y
# Focus on the viewport center where the face is
vx1 = x + int(w * 0.15)
vy1 = y + int(h * 0.05)
vx2 = x + int(w * 0.55)
vy2 = y + int(h * 0.50)

img = ImageGrab.grab(bbox=(vx1, vy1, vx2, vy2))
# Save at full resolution
draw = ImageDraw.Draw(img)
draw.text((10, 10), "Frame 30: TH (jaw_openExtreme=1.0)", fill=(255, 255, 100))
img.save("c:/Users/yuval/src/aivatar/ue_th_closeup.png")
print(f"Saved TH closeup: {img.size}")

win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
