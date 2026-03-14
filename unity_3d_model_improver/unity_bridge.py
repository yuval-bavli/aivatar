"""
Unity agent bridge wrapper.

Communicates with Unity Editor via file-based protocol:
  Write command → unity/aivatar/agent_request.txt
  Wait for result → unity/aivatar/agent_result.txt

The CaptureScreenshot.cs editor script in the Unity project handles
these files and supports three commands:
  screenshot                  — captures the main camera, returns file path
  refresh                     — triggers AssetDatabase.Refresh(), returns "ready"
  execute ClassName.Method    — calls a static C# method, returns its string result

This module also provides direct .mat file reading (no Unity bridge needed)
since Unity material files are plain YAML that Python can parse directly.
"""

from __future__ import annotations
import os
import time
import pathlib
import re
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────

_REPO_ROOT = pathlib.Path(__file__).parent.parent.resolve()
_PROJECT   = _REPO_ROOT / "unity" / "aivatar"
_REQUEST   = _PROJECT / "agent_request.txt"
_RESULT    = _PROJECT / "agent_result.txt"

MATERIALS_DIR = _PROJECT / "Assets" / "Models" / "Avatar" / "Materials"

# Materials the improver is allowed to edit (by filename without extension)
EDITABLE_MATERIALS = {
    "Eyebrows",
    "haircut",
    "MI_Face_EyelashesHiLODs",
    "M_Hide",
    "M_Hide_6",
    "MID_M_DG_bodyShapeB_Shirt_70",
    "MID_M_DG_bodyShapeB_Short_71",
}


# ── Agent bridge ────────────────────────────────────────────────────────────

def _send_command(command: str, timeout: float = 30.0) -> str:
    """Send a command to Unity and wait for the result."""
    # Clear any stale result
    if _RESULT.exists():
        _RESULT.unlink()

    _REQUEST.write_text(command, encoding="utf-8")

    deadline = time.time() + timeout
    while time.time() < deadline:
        if _RESULT.exists():
            result = _RESULT.read_text(encoding="utf-8").strip()
            return result
        time.sleep(0.2)

    raise TimeoutError(f"Unity did not respond within {timeout}s to command: {command!r}")


def screenshot(timeout: float = 30.0) -> pathlib.Path:
    """Trigger a screenshot in Unity and return the saved file path."""
    result = _send_command("screenshot", timeout=timeout)
    if result.startswith("ERROR"):
        raise RuntimeError(f"Screenshot failed: {result}")
    # Result is a Windows path like C:/Users/.../screenshot_...png
    path = pathlib.Path(result.replace("\\", "/"))
    if not path.exists():
        raise FileNotFoundError(f"Screenshot file not found: {path}")
    return path


def refresh(timeout: float = 60.0) -> None:
    """Trigger AssetDatabase.Refresh() in Unity and wait for recompile."""
    result = _send_command("refresh", timeout=timeout)
    if result not in ("ready", "OK"):
        raise RuntimeError(f"Refresh returned unexpected result: {result}")


def execute(class_method: str, timeout: float = 30.0) -> str:
    """Call a static C# method in Unity (e.g. 'MyClass.MyMethod')."""
    result = _send_command(f"execute {class_method}", timeout=timeout)
    if result.startswith("ERROR"):
        raise RuntimeError(f"Execute failed: {result}")
    return result


# ── .mat file reading ───────────────────────────────────────────────────────

def read_material_properties(mat_name: str) -> dict:
    """
    Read a .mat file and return its key properties as a plain dict.

    Returns:
        {
          "name": "haircut",
          "floats": {"_Cutoff": 0.15, "_Smoothness": 0.2, ...},
          "colors": {"_BaseColor": [0.22, 0.15, 0.1, 1.0], ...},
        }
    """
    mat_path = MATERIALS_DIR / f"{mat_name}.mat"
    if not mat_path.exists():
        raise FileNotFoundError(f"Material not found: {mat_path}")

    text = mat_path.read_text(encoding="utf-8")

    floats: dict[str, float] = {}
    colors: dict[str, list] = {}

    # Parse floats:  - _Cutoff: 0.15
    for m in re.finditer(r"- (\w+): ([0-9\.\-e]+)\s*$", text, re.MULTILINE):
        try:
            floats[m.group(1)] = float(m.group(2))
        except ValueError:
            pass

    # Parse colors:  - _BaseColor: {r: 0.22, g: 0.15, b: 0.1, a: 1}
    for m in re.finditer(
        r"- (\w+): \{r: ([0-9.\-e]+), g: ([0-9.\-e]+), b: ([0-9.\-e]+), a: ([0-9.\-e]+)\}",
        text,
    ):
        try:
            colors[m.group(1)] = [
                float(m.group(2)),
                float(m.group(3)),
                float(m.group(4)),
                float(m.group(5)),
            ]
        except ValueError:
            pass

    return {"name": mat_name, "floats": floats, "colors": colors}


def read_all_editable_materials() -> dict:
    """Return a dict of {mat_name: properties} for all editable materials."""
    result = {}
    for name in EDITABLE_MATERIALS:
        try:
            result[name] = read_material_properties(name)
        except FileNotFoundError:
            pass
    return result
