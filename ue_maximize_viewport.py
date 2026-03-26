"""Maximize UE viewport and take screenshot."""
import win32gui, win32con, win32api, time, ctypes
from PIL import ImageGrab, Image
import os

# Find UE window
results = []
def callback(hwnd, extra):
    title = win32gui.GetWindowText(hwnd)
    if 'Unreal Editor' in title and win32gui.IsWindowVisible(hwnd):
        results.append((hwnd, title))
win32gui.EnumWindows(callback, None)

if not results:
    print("ERROR: Unreal Editor window not found")
    exit(1)

hwnd = results[0][0]

# Bring to front and maximize
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
time.sleep(1)

# Get window rect
rect = win32gui.GetWindowRect(hwnd)
x, y, x2, y2 = rect
w, h = x2 - x, y2 - y
print(f"Window: {w}x{h} at ({x},{y})")

# Capture full window
img = ImageGrab.grab(bbox=(x, y, x2, y2))
scale = min(900/w, 700/h, 1.0)
img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
img.save("c:/Users/yuval/src/aivatar/ue_fullwin.png", optimize=True)
print(f"Saved: {img.size}, {os.path.getsize('c:/Users/yuval/src/aivatar/ue_fullwin.png')} bytes")
