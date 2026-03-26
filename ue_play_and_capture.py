"""Play the sequence, pause at specific frames, and capture to verify evaluation."""
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

rect = win32gui.GetWindowRect(hwnd)
x, y, x2, y2 = rect
w, h = x2 - x, y2 - y
vx1 = x + int(w * 0.10)
vy1 = y + int(h * 0.04)
vx2 = x + int(w * 0.58)
vy2 = y + int(h * 0.52)

# Start playback from beginning
ue_exec("import unreal; unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0)")
time.sleep(0.5)
ue_exec("import unreal; unreal.LevelSequenceEditorBlueprintLibrary.play()")
time.sleep(0.3)  # Let it run briefly
ue_exec("import unreal; unreal.LevelSequenceEditorBlueprintLibrary.pause()")
time.sleep(0.5)

# Now scrub to frame 0, capture
ue_exec("import unreal; unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0)")
time.sleep(1.0)
img0 = ImageGrab.grab(bbox=(vx1, vy1, vx2, vy2))

# Play to frame 100 by scrubbing then play/pause
ue_exec("import unreal; unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(100)")
time.sleep(0.3)
ue_exec("import unreal; unreal.LevelSequenceEditorBlueprintLibrary.play()")
time.sleep(0.1)
ue_exec("import unreal; unreal.LevelSequenceEditorBlueprintLibrary.pause()")
time.sleep(1.0)
img100 = ImageGrab.grab(bbox=(vx1, vy1, vx2, vy2))

# Side by side
iw, ih = img0.size
grid = Image.new('RGB', (iw * 2, ih + 30), (20, 20, 20))
draw0 = ImageDraw.Draw(img0)
draw0.text((20, 20), "F0: sil (jaw=0)", fill=(255, 255, 0))
draw100 = ImageDraw.Draw(img100)
draw100.text((20, 20), "F100: aa (jaw=-0.8)", fill=(255, 255, 0))
grid.paste(img0, (0, 28))
grid.paste(img100, (iw, 28))
grid.save("c:/Users/yuval/src/aivatar/ue_play_test.png")
print(f"Saved: {grid.size}")

win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
