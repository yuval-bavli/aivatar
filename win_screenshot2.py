"""Capture Unreal Editor viewport - wider crop to see the character face."""
import win32gui
from PIL import ImageGrab, Image
import os, sys

out_path = sys.argv[1] if len(sys.argv) > 1 else "c:/Users/yuval/src/aivatar/ue_viewport.png"

results = []
def callback(hwnd, extra):
    title = win32gui.GetWindowText(hwnd)
    if 'Unreal Editor' in title and win32gui.IsWindowVisible(hwnd):
        results.append((hwnd, title))
win32gui.EnumWindows(callback, None)

if not results:
    print("ERROR: Unreal Editor window not found")
    sys.exit(1)

hwnd = results[0][0]
rect = win32gui.GetWindowRect(hwnd)
x, y, x2, y2 = rect
w, h = x2 - x, y2 - y

# Wider crop - center of the viewport
vx1 = x + int(w * 0.15)
vy1 = y + int(h * 0.05)
vx2 = x + int(w * 0.75)
vy2 = y + int(h * 0.65)

img = ImageGrab.grab(bbox=(vx1, vy1, vx2, vy2))
img = img.resize((480, 300), Image.LANCZOS)
img.save(out_path, optimize=True)
print(f"Saved: {img.size}, {os.path.getsize(out_path)} bytes")
