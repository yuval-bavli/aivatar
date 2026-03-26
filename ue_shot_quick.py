"""Quick screenshot of current frame."""
import json, urllib.request, time
import win32gui, win32con
from PIL import ImageGrab, Image
import os

results = []
def callback(hwnd, extra):
    title = win32gui.GetWindowText(hwnd)
    if 'Unreal Editor' in title and win32gui.IsWindowVisible(hwnd):
        results.append((hwnd, title))
win32gui.EnumWindows(callback, None)
hwnd = results[0][0]
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
time.sleep(0.5)

rect = win32gui.GetWindowRect(hwnd)
x, y, x2, y2 = rect
w, h = x2 - x, y2 - y

# Full window capture
img = ImageGrab.grab(bbox=(x, y, x2, y2))
scale = min(900/w, 700/h, 1.0)
img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
img.save("c:/Users/yuval/src/aivatar/ue_quick.png", optimize=True)
print(f"Saved: {img.size}")

win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
