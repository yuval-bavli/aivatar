"""Take large side-by-side of frame 0 vs 30 vs 100."""
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

# Full viewport
vx1 = x + int(w * 0.10)
vy1 = y + int(h * 0.04)
vx2 = x + int(w * 0.58)
vy2 = y + int(h * 0.52)

frames = [(0, "F0: sil (rest)"), (30, "F30: TH (jaw=-0.5, openExtreme=1.0)"), (100, "F100: aa (jaw=-0.8)")]

images = []
for frame, name in frames:
    ue_exec(f"import unreal; unreal.LevelSequenceEditorBlueprintLibrary.set_current_time({frame})")
    time.sleep(1.0)
    img = ImageGrab.grab(bbox=(vx1, vy1, vx2, vy2))
    images.append((img, name))

# Create grid at full capture resolution
iw, ih = images[0][0].size
cell_h = ih + 30
grid = Image.new('RGB', (iw * 3, cell_h), (20, 20, 20))
for i, (img, name) in enumerate(images):
    draw_cell = Image.new('RGB', (iw, cell_h), (20, 20, 20))
    draw = ImageDraw.Draw(draw_cell)
    draw.text((10, 5), name, fill=(255, 255, 100))
    draw_cell.paste(img, (0, 28))
    grid.paste(draw_cell, (i * iw, 0))

grid.save("c:/Users/yuval/src/aivatar/ue_th_vs_aa.png")
print(f"Saved: {grid.size}")

win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
