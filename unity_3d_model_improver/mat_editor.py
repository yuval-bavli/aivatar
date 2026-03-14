"""
Unity .mat file editor.

Edits float and color properties inside Unity URP material YAML files
using regex-based substitution.  Does NOT re-serialize the whole file —
only the specific property values are changed, leaving all GUIDs and
structural YAML intact.

Supported change formats (as produced by the vision model):
  {"material": "haircut",  "property": "_Cutoff",    "value": 0.25}
  {"material": "haircut",  "property": "_BaseColor",  "value": [0.22, 0.15, 0.1, 1.0]}

Also supports _Color (legacy) in sync with _BaseColor.
"""

from __future__ import annotations
import re
import pathlib
import shutil
import datetime
from typing import Union

_REPO_ROOT = pathlib.Path(__file__).parent.parent.resolve()
_MATERIALS_DIR = _REPO_ROOT / "unity" / "aivatar" / "Assets" / "Models" / "Avatar" / "Materials"
_BACKUP_DIR = pathlib.Path(__file__).parent / "mat_backups"

ColorValue = list  # [r, g, b, a]


# ── Backup ─────────────────────────────────────────────────────────────────

def _backup(mat_path: pathlib.Path) -> None:
    """Write a timestamped backup the first time we touch a .mat file."""
    _BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = _BACKUP_DIR / f"{mat_path.stem}_{stamp}.mat"
    shutil.copy2(mat_path, dest)


# ── Float property ──────────────────────────────────────────────────────────

def _set_float(text: str, prop: str, value: float) -> str:
    """Replace  - <prop>: <old_value>  with  - <prop>: <new_value>"""
    pattern = rf"(- {re.escape(prop)}: )[0-9.\-e]+"
    new_text = re.sub(pattern, rf"\g<1>{value:.6g}", text)
    if new_text == text:
        raise KeyError(f"Float property '{prop}' not found in material")
    return new_text


# ── Color property ──────────────────────────────────────────────────────────

def _fmt_color(r: float, g: float, b: float, a: float) -> str:
    return f"{{r: {r:.8g}, g: {g:.8g}, b: {b:.8g}, a: {a:.8g}}}"


def _set_color(text: str, prop: str, rgba: ColorValue) -> str:
    """Replace  - <prop>: {r: ..., g: ..., b: ..., a: ...}"""
    r, g, b, a = rgba[0], rgba[1], rgba[2], (rgba[3] if len(rgba) > 3 else 1.0)
    pattern = (
        rf"(- {re.escape(prop)}: )"
        r"\{r: [0-9.\-e]+, g: [0-9.\-e]+, b: [0-9.\-e]+, a: [0-9.\-e]+\}"
    )
    replacement = rf"\g<1>{_fmt_color(r, g, b, a)}"
    new_text = re.sub(pattern, replacement, text)
    if new_text == text:
        raise KeyError(f"Color property '{prop}' not found in material")
    return new_text


# ── Public API ──────────────────────────────────────────────────────────────

def apply_change(mat_name: str, prop: str, value: Union[float, ColorValue]) -> None:
    """
    Apply a single property change to a .mat file.

    mat_name : material filename without extension (e.g. "haircut")
    prop     : shader property name (e.g. "_Cutoff", "_BaseColor")
    value    : float or [r, g, b, a] list
    """
    mat_path = _MATERIALS_DIR / f"{mat_name}.mat"
    if not mat_path.exists():
        raise FileNotFoundError(f"Material not found: {mat_path}")

    text = mat_path.read_text(encoding="utf-8")
    _backup(mat_path)

    if isinstance(value, (int, float)):
        text = _set_float(text, prop, float(value))
    elif isinstance(value, (list, tuple)):
        text = _set_color(text, prop, list(value))
        # Keep legacy _Color in sync with _BaseColor
        if prop == "_BaseColor":
            try:
                text = _set_color(text, "_Color", list(value))
            except KeyError:
                pass
    else:
        raise TypeError(f"Unsupported value type: {type(value)}")

    mat_path.write_text(text, encoding="utf-8")
    print(f"[mat_editor] {mat_name}.{prop} = {value}")


def apply_changes(changes: list[dict]) -> list[str]:
    """
    Apply a list of change dicts from the vision model.

    Each dict must have keys: "material", "property", "value".
    Returns a list of error strings (empty list = all OK).
    """
    errors = []
    for ch in changes:
        mat  = ch.get("material", "")
        prop = ch.get("property", "")
        val  = ch.get("value")
        if not mat or not prop or val is None:
            errors.append(f"Skipping malformed change: {ch}")
            continue
        try:
            apply_change(mat, prop, val)
        except Exception as e:
            errors.append(f"Failed {mat}.{prop}: {e}")
    return errors
