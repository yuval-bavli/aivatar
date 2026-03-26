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
if not results:
    print("Unreal Editor not found")
    exit(1)

hwnd = results[0][0]
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
time.sleep(1)

rect = win32gui.GetWindowRect(hwnd)
x, y, x2, y2 = rect
w, h = x2 - x, y2 - y

# Tighter crop on the face to save bytes
# Based on old crop: vx1 = +10%, vy1 = +4%, vx2 = +58%, vy2 = +52%
# Face is probably in the middle of that region
vx1 = x + int(w * 0.25)
vy1 = y + int(h * 0.15)
vx2 = x + int(w * 0.45)
vy2 = y + int(h * 0.45)

print(f"Window: {w}x{h}, Crop: {vx1},{vy1} to {vx2},{vy2}")

ue_exec("import unreal; unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(30*800)")
time.sleep(1.0)
img = ImageGrab.grab(bbox=(vx1, vy1, vx2, vy2))
img = img.resize((cc_w:=int((vx2-vx1)*0.5), cc_h:=int((vy2-vy1)*0.5)), Image.LANCZOS)
img.save("c:/Users/yuval/src/aivatar/th_before.png", optimize=True)
print("Saved th_before.png")

win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
