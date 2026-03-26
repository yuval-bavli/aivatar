"""Send Ctrl+Z keystrokes to UE to undo changes."""
import win32gui, win32con, win32api, time, ctypes

# Find UE window
results = []
def callback(hwnd, extra):
    title = win32gui.GetWindowText(hwnd)
    if 'Unreal Editor' in title and win32gui.IsWindowVisible(hwnd):
        results.append((hwnd, title))
win32gui.EnumWindows(callback, None)

if not results:
    print("ERROR: No UE window")
    exit(1)

hwnd = results[0][0]

# Bring to foreground
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
time.sleep(0.3)

# Use SendInput for Ctrl+Z
import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_Z = 0x5A

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]

def send_ctrl_z():
    inputs = (INPUT * 4)()
    # Ctrl down
    inputs[0].type = INPUT_KEYBOARD
    inputs[0]._input.ki.wVk = VK_CONTROL
    # Z down
    inputs[1].type = INPUT_KEYBOARD
    inputs[1]._input.ki.wVk = VK_Z
    # Z up
    inputs[2].type = INPUT_KEYBOARD
    inputs[2]._input.ki.wVk = VK_Z
    inputs[2]._input.ki.dwFlags = KEYEVENTF_KEYUP
    # Ctrl up
    inputs[3].type = INPUT_KEYBOARD
    inputs[3]._input.ki.wVk = VK_CONTROL
    inputs[3]._input.ki.dwFlags = KEYEVENTF_KEYUP

    user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))

# Send many Ctrl+Z
for i in range(50):
    send_ctrl_z()
    time.sleep(0.05)

print(f"Sent 50 Ctrl+Z keystrokes")
time.sleep(1)

# Remove topmost
win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
