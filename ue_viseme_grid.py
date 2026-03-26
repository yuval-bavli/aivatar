"""Capture a 5x3 grid of all 15 visemes by scrubbing + window screenshot."""
import json, urllib.request, time, os
import win32gui, win32con
from PIL import ImageGrab, Image, ImageDraw, ImageFont

UE_API = "http://127.0.0.1:30010/remote/object/call"

def ue_exec(code):
    payload = json.dumps({
        "objectPath": "/Script/PythonScriptPlugin.Default__PythonScriptLibrary",
        "functionName": "ExecutePythonCommand",
        "parameters": {"PythonCommand": code}
    }).encode()
    req = urllib.request.Request(UE_API, data=payload,
        headers={"Content-Type": "application/json"}, method="PUT")
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read().decode())

# Find UE window
results = []
def callback(hwnd, extra):
    title = win32gui.GetWindowText(hwnd)
    if 'Unreal Editor' in title and win32gui.IsWindowVisible(hwnd):
        results.append((hwnd, title))
win32gui.EnumWindows(callback, None)
hwnd = results[0][0]

# Bring to top
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
time.sleep(1)

rect = win32gui.GetWindowRect(hwnd)
x, y, x2, y2 = rect
w, h = x2 - x, y2 - y

# Viewport area (adjusted for maximized layout)
vx1 = x + int(w * 0.12)
vy1 = y + int(h * 0.06)
vx2 = x + int(w * 0.56)
vy2 = y + int(h * 0.50)

visemes = [
    (0, "sil"), (10, "PP"), (20, "FF"), (30, "TH"), (40, "DD"),
    (50, "kk"), (60, "CH"), (70, "SS"), (80, "nn"), (90, "RR"),
    (100, "aa"), (110, "E"), (120, "ih"), (130, "oh"), (140, "ou")
]

cell_w, cell_h = 240, 180
cols, rows = 5, 3
grid = Image.new('RGB', (cols * cell_w, rows * cell_h), (30, 30, 30))

for i, (frame, name) in enumerate(visemes):
    # Scrub to frame
    ue_exec(f"import unreal; unreal.LevelSequenceEditorBlueprintLibrary.set_current_time({frame * 800})")
    time.sleep(0.3)

    # Capture viewport
    img = ImageGrab.grab(bbox=(vx1, vy1, vx2, vy2))
    img = img.resize((cell_w, cell_h - 20), Image.LANCZOS)

    col = i % cols
    row = i // cols

    # Add label
    cell = Image.new('RGB', (cell_w, cell_h), (30, 30, 30))
    draw = ImageDraw.Draw(cell)
    label = f"F{frame}: {name}"
    draw.text((5, 2), label, fill=(255, 255, 100))
    cell.paste(img, (0, 18))
    grid.paste(cell, (col * cell_w, row * cell_h))

grid.save("c:/Users/yuval/src/aivatar/ue_viseme_grid.png", optimize=True)
print(f"Grid saved: {grid.size}, {os.path.getsize('c:/Users/yuval/src/aivatar/ue_viseme_grid.png')} bytes")

# Remove topmost
win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
