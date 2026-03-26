"""Definitive test: take screenshots at frame 0 and 100, side by side, large."""
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

# First: play briefly then stop to force evaluation pipeline refresh
ue_exec("import unreal; unreal.LevelSequenceEditorBlueprintLibrary.play()")
time.sleep(0.5)
ue_exec("import unreal; unreal.LevelSequenceEditorBlueprintLibrary.pause()")
time.sleep(0.5)

frames = [(0, "F0: sil (jaw.Y=0)"), (100, "F100: aa (jaw.Y=-0.8)")]
images = []
for frame, label in frames:
    ue_exec(f"import unreal; unreal.LevelSequenceEditorBlueprintLibrary.set_current_time({frame})")
    time.sleep(1.5)  # extra wait for evaluation
    img = ImageGrab.grab(bbox=(vx1, vy1, vx2, vy2))
    images.append((img, label))

iw, ih = images[0][0].size
grid = Image.new('RGB', (iw * 2, ih + 30), (20, 20, 20))
for i, (img, label) in enumerate(images):
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), label, fill=(255, 255, 0))
    grid.paste(img, (i * iw, 28))

grid.save("c:/Users/yuval/src/aivatar/ue_definitive_test.png")
print(f"Saved: {grid.size}")

win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
