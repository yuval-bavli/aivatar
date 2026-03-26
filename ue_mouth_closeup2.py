"""Take full viewport screenshots for 3 frames, then crop to mouth area."""
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

# Full viewport area (same as the working ue_compare_correct.py)
vx1 = x + int(w * 0.10)
vy1 = y + int(h * 0.04)
vx2 = x + int(w * 0.58)
vy2 = y + int(h * 0.52)

frames = [(0, "sil"), (10, "PP"), (30, "TH"), (100, "aa")]
cell_w, cell_h = 480, 340

grid = Image.new('RGB', (len(frames) * cell_w, cell_h), (30, 30, 30))
for i, (frame, name) in enumerate(frames):
    ue_exec(f"import unreal; unreal.LevelSequenceEditorBlueprintLibrary.set_current_time({frame})")
    time.sleep(0.8)
    img = ImageGrab.grab(bbox=(vx1, vy1, vx2, vy2))
    img = img.resize((cell_w, cell_h - 24), Image.LANCZOS)
    cell = Image.new('RGB', (cell_w, cell_h), (30, 30, 30))
    draw = ImageDraw.Draw(cell)
    draw.text((10, 4), f"F{frame}: {name}", fill=(255, 255, 100))
    cell.paste(img, (0, 22))
    grid.paste(cell, (i * cell_w, 0))

grid.save("c:/Users/yuval/src/aivatar/ue_viseme_compare2.png")
print(f"Saved: {grid.size}")

win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
