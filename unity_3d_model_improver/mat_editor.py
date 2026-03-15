"""
Unity .mat file editor.

Edits float, color, AND keyword properties inside Unity URP material YAML files
using regex-based substitution.  Does NOT re-serialize the whole file —
only the specific property values are changed, leaving all GUIDs and
structural YAML intact.

Supported change formats (as produced by the vision model):
  {"material": "haircut",  "property": "_Cutoff",    "value": 0.25}
  {"material": "haircut",  "property": "_BaseColor",  "value": [0.22, 0.15, 0.1, 1.0]}
  {"material": "haircut",  "action": "enable_keyword",  "keyword": "_ALPHATEST_ON"}
  {"material": "haircut",  "action": "disable_keyword", "keyword": "_SURFACE_TYPE_TRANSPARENT"}
  {"material": "haircut",  "action": "set_render_queue", "value": 2450}

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


# ── Keyword properties ─────────────────────────────────────────────────────

def _enable_keyword(text: str, keyword: str) -> str:
    """Move a keyword to m_ValidKeywords (and remove from m_InvalidKeywords)."""
    text = _remove_from_keyword_list(text, "m_InvalidKeywords", keyword)
    text = _add_to_keyword_list(text, "m_ValidKeywords", keyword)
    return text


def _disable_keyword(text: str, keyword: str) -> str:
    """Move a keyword to m_InvalidKeywords (and remove from m_ValidKeywords)."""
    text = _remove_from_keyword_list(text, "m_ValidKeywords", keyword)
    text = _add_to_keyword_list(text, "m_InvalidKeywords", keyword)
    return text


def _remove_from_keyword_list(text: str, list_name: str, keyword: str) -> str:
    """Remove a keyword entry from a YAML keyword list."""
    pattern = rf"(  {list_name}:\n)((?:  - \w+\n)*)"
    match = re.search(pattern, text)
    if not match:
        return text

    list_header = match.group(1)
    entries = match.group(2)
    new_entries = re.sub(rf"  - {re.escape(keyword)}\n", "", entries)
    if new_entries == entries:
        return text

    if not new_entries.strip():
        return text[:match.start()] + f"  {list_name}: []\n" + text[match.end():]

    return text[:match.start()] + list_header + new_entries + text[match.end():]


def _add_to_keyword_list(text: str, list_name: str, keyword: str) -> str:
    """Add a keyword entry to a YAML keyword list."""
    check_pattern = rf"  {list_name}:\n(?:  - \w+\n)*  - {re.escape(keyword)}\n"
    if re.search(check_pattern, text):
        return text

    empty_pattern = rf"(  {list_name}: )\[\]"
    empty_match = re.search(empty_pattern, text)
    if empty_match:
        replacement = f"  {list_name}:\n  - {keyword}"
        return text[:empty_match.start()] + replacement + text[empty_match.end():]

    pattern = rf"(  {list_name}:\n(?:  - \w+\n)*)"
    match = re.search(pattern, text)
    if match:
        return text[:match.end()] + f"  - {keyword}\n" + text[match.end():]

    raise KeyError(f"Keyword list '{list_name}' not found in material")


def _set_render_queue(text: str, value: int) -> str:
    """Set m_CustomRenderQueue value."""
    pattern = r"(  m_CustomRenderQueue: )-?\d+"
    new_text = re.sub(pattern, rf"\g<1>{value}", text)
    if new_text == text:
        raise KeyError("m_CustomRenderQueue not found in material")
    return new_text


def _set_render_type_tag(text: str, render_type: str) -> str:
    """Set the RenderType string tag."""
    pattern = r"(  stringTagMap:\n    RenderType: )\w+"
    match = re.search(pattern, text)
    if match:
        return text[:match.start()] + f"  stringTagMap:\n    RenderType: {render_type}" + text[match.end():]

    empty_pattern = r"  stringTagMap: \{\}"
    if re.search(empty_pattern, text):
        replacement = f"  stringTagMap:\n    RenderType: {render_type}"
        return re.sub(empty_pattern, replacement, text)

    return text


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


def apply_keyword_change(mat_name: str, action: str, keyword: str) -> None:
    """
    Enable or disable a shader keyword in a .mat file.

    mat_name : material filename without extension
    action   : "enable_keyword" or "disable_keyword"
    keyword  : shader keyword (e.g. "_ALPHATEST_ON", "_SURFACE_TYPE_TRANSPARENT")
    """
    mat_path = _MATERIALS_DIR / f"{mat_name}.mat"
    if not mat_path.exists():
        raise FileNotFoundError(f"Material not found: {mat_path}")

    text = mat_path.read_text(encoding="utf-8")
    _backup(mat_path)

    if action == "enable_keyword":
        text = _enable_keyword(text, keyword)
    elif action == "disable_keyword":
        text = _disable_keyword(text, keyword)
    else:
        raise ValueError(f"Unknown keyword action: {action}")

    mat_path.write_text(text, encoding="utf-8")
    print(f"[mat_editor] {mat_name}: {action} {keyword}")


def apply_render_queue(mat_name: str, value: int) -> None:
    """Set the custom render queue for a material."""
    mat_path = _MATERIALS_DIR / f"{mat_name}.mat"
    if not mat_path.exists():
        raise FileNotFoundError(f"Material not found: {mat_path}")

    text = mat_path.read_text(encoding="utf-8")
    _backup(mat_path)
    text = _set_render_queue(text, value)
    mat_path.write_text(text, encoding="utf-8")
    print(f"[mat_editor] {mat_name}: renderQueue = {value}")


def apply_changes(changes: list[dict]) -> list[str]:
    """
    Apply a list of change dicts from the vision model.

    Supports three formats:
      {"material": "X", "property": "Y", "value": Z}          — float/color
      {"material": "X", "action": "enable_keyword|disable_keyword", "keyword": "Y"}
      {"material": "X", "action": "set_render_queue", "value": N}

    Returns a list of error strings (empty list = all OK).
    """
    errors = []
    for ch in changes:
        mat = ch.get("material", "")
        action = ch.get("action", "")

        try:
            if action == "enable_keyword" or action == "disable_keyword":
                keyword = ch.get("keyword", "")
                if not mat or not keyword:
                    errors.append(f"Skipping malformed keyword change: {ch}")
                    continue
                apply_keyword_change(mat, action, keyword)

            elif action == "set_render_queue":
                val = ch.get("value")
                if not mat or val is None:
                    errors.append(f"Skipping malformed render queue change: {ch}")
                    continue
                apply_render_queue(mat, int(val))

            else:
                # Legacy float/color change
                prop = ch.get("property", "")
                val = ch.get("value")
                if not mat or not prop or val is None:
                    errors.append(f"Skipping malformed change: {ch}")
                    continue
                apply_change(mat, prop, val)

        except Exception as e:
            errors.append(f"Failed on {ch}: {e}")

    return errors
