"""
audit.py — Visual auditor for the MetaHuman Unity model.

Compares the live Unity render to a reference photo using a local vision
model (via Ollama), then prints one of two results:

  DONE
  The Unity render matches the reference well enough.

  or

  ISSUES FOUND
  - eyebrows: too light, should be darker brown
  - eyelashes: too bold/thick, need higher _Cutoff
  - hair: color too warm, should be cooler dark brown

Supports multiple modes:
  --mode standard      : Original qwen3-vl:8b audit (default)
  --mode upgraded      : qwen2.5-vl:32b with full material context
  --with-materials     : Include all material properties in the prompt
  --compare            : Compare two screenshots (first vs last)

Usage:
    python audit.py [--ref PATH] [--mode standard|upgraded] [--with-materials] [--compare FIRST LAST]
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
import sys

import requests
import vram_manager
import unity_bridge

# ── Paths ──────────────────────────────────────────────────────────────────

REFERENCE_PHOTO = pathlib.Path(__file__).parent / "3d_model_desired.png"

# ── Ollama ─────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"

# ── Upgraded model ─────────────────────────────────────────────────────────

UPGRADED_MODEL = "qwen2.5vl:32b"

# ── Prompts ────────────────────────────────────────────────────────────────

AUDIT_PROMPT = """\
You are a 3D rendering expert comparing a Unity URP render to an Unreal Engine reference.
Unity has inherent rendering differences from Unreal (different lighting, no subsurface scattering,
card-based hair). Minor differences due to renderer limitations are ACCEPTABLE.

IMAGE 1: Reference MetaHuman (Unreal Engine).
IMAGE 2: Unity URP render.

The eyes (sclera, iris, cornea) have already been fixed — do NOT comment on eye color or shape.

Evaluate ONLY these three aspects. For each, decide if it is ACCEPTABLE (close enough given
Unity's limitations) or NEEDS MAJOR IMPROVEMENT:

  1. EYEBROWS — color and darkness relative to reference (minor thickness differences OK)
  2. EYELASHES — natural appearance; subtle dark edge around eye is acceptable as a Unity artifact
  3. HAIR — overall color family should match reference (warm brown)

For each aspect that NEEDS MAJOR IMPROVEMENT, give one concrete ACTION instruction.

On the final line output exactly one of:
  VERDICT: DONE
  VERDICT: NEEDS CHANGES
"""

UPGRADED_AUDIT_PROMPT = """\
You are a Unity URP rendering expert. You are comparing a Unity URP render (IMAGE 2)
to an Unreal Engine MetaHuman reference (IMAGE 1).

MATERIAL PROPERTIES (current state of editable materials):
{material_context}

Unity inherently differs from Unreal (no subsurface scattering, card-based hair vs groom).
Minor differences are ACCEPTABLE. The eyes are already fixed — do NOT comment on them.

Evaluate ONLY these three aspects:

1. EYEBROWS — Are they visible and approximately matching the reference color/position?
   Current state: Eyebrows may be baked into the face texture (T_Head_BC_VT_Brows.png)
   or rendered via a separate mesh with the Eyebrows.mat material.

2. EYELASHES — Are they too thick/bold compared to reference?
   Key material: MI_Face_EyelashesHiLODs.mat
   Key properties: _AlphaClip (must be 1 to enable clipping), _Cutoff (higher = thinner),
   m_ValidKeywords must include _ALPHATEST_ON for alpha clipping to work.
   If _AlphaClip is 0 or _ALPHATEST_ON is not in m_ValidKeywords, THAT is the root cause.

3. HAIR — Does the color family match? Does it look overly glossy/plastic?
   Key material: haircut.mat
   Key properties: _Smoothness (lower = more matte, hair should be 0.3-0.5 not 0.9+),
   _BaseColor (should be warm dark brown), _Cutoff (hair card alpha threshold).

For each aspect that NEEDS IMPROVEMENT, give a SPECIFIC fix using one of these formats:
  - Float change: {{"material": "name", "property": "_Prop", "value": 0.5}}
  - Color change: {{"material": "name", "property": "_BaseColor", "value": [r, g, b, a]}}
  - Enable keyword: {{"material": "name", "action": "enable_keyword", "keyword": "_ALPHATEST_ON"}}
  - Disable keyword: {{"material": "name", "action": "disable_keyword", "keyword": "_SURFACE_TYPE_TRANSPARENT"}}
  - Render queue: {{"material": "name", "action": "set_render_queue", "value": 2450}}

On the final line output exactly one of:
  VERDICT: DONE
  VERDICT: NEEDS CHANGES
"""

COMPARISON_PROMPT = """\
You are comparing two Unity screenshots of the same MetaHuman avatar taken at different times.

IMAGE 1: The BEFORE screenshot (start of improvement attempt).
IMAGE 2: The AFTER screenshot (current state after {iterations} iterations).
IMAGE 3: The REFERENCE (original MetaHuman from Unreal Engine).

Evaluate whether ANY of these three problems have been FIXED or NOTICEABLY IMPROVED
when comparing BEFORE to AFTER:

1. EYEBROWS — Were they missing/invisible before? Are they visible now?
2. EYELASHES — Were they too thick/bold before? Are they thinner/more natural now?
3. HAIR — Did it look polygon-like/plastic before? Does it look more natural now?

For each, state: FIXED, IMPROVED, UNCHANGED, or WORSE.

Then on the final line:
  If at least one aspect is FIXED or IMPROVED: PROGRESS: YES
  If all aspects are UNCHANGED or WORSE: PROGRESS: NO
"""


def _encode(path: pathlib.Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def _get_material_context() -> str:
    """Read all editable material properties and format as context string."""
    try:
        materials = unity_bridge.read_all_editable_materials()
        lines = []
        for name, props in sorted(materials.items()):
            lines.append(f"\n=== {name}.mat ===")
            if props.get("floats"):
                for k, v in sorted(props["floats"].items()):
                    lines.append(f"  {k}: {v}")
            if props.get("colors"):
                for k, v in sorted(props["colors"].items()):
                    lines.append(f"  {k}: {v}")
            # Also read keyword state from the raw .mat file
            mat_path = unity_bridge.MATERIALS_DIR / f"{name}.mat"
            if mat_path.exists():
                text = mat_path.read_text(encoding="utf-8")
                valid_kw = re.findall(r"m_ValidKeywords:\n((?:  - \w+\n)*)", text)
                invalid_kw = re.findall(r"m_InvalidKeywords:\n((?:  - \w+\n)*)", text)
                if valid_kw:
                    keywords = [line.strip("- \n") for line in valid_kw[0].strip().split("\n") if line.strip()]
                    lines.append(f"  m_ValidKeywords: {keywords}")
                else:
                    # Check for empty list
                    if "m_ValidKeywords: []" in text:
                        lines.append("  m_ValidKeywords: []")
                if invalid_kw:
                    keywords = [line.strip("- \n") for line in invalid_kw[0].strip().split("\n") if line.strip()]
                    lines.append(f"  m_InvalidKeywords: {keywords}")
                # Render queue
                rq_match = re.search(r"m_CustomRenderQueue: (-?\d+)", text)
                if rq_match:
                    lines.append(f"  m_CustomRenderQueue: {rq_match.group(1)}")
        return "\n".join(lines)
    except Exception as e:
        return f"(Could not read materials: {e})"


def _call_ollama(model: str, prompt: str, images: list[str], timeout: int = 300) -> str:
    """Call Ollama API and return cleaned response text."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt, "images": images}],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 4096, "num_gpu": 20},  # 20 GPU layers, rest spill to CPU RAM — allows large models with limited VRAM
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()

        if "error" in body:
            err = body["error"].lower()
            if "out of memory" in err or "oom" in err:
                return f"OOM:{body['error']}"
            print(f"ERROR from Ollama: {body['error']}", file=sys.stderr)
            sys.exit(1)

        raw = body["message"]["content"]
        # Strip <think>...</think> blocks (qwen3 inline chain-of-thought)
        clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        if not clean:
            thinking = body["message"].get("thinking", "")
            after = re.split(r"</think>", thinking, maxsplit=1)
            clean = after[-1].strip() if len(after) > 1 else ""
        return clean if clean else raw

    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to Ollama. Run: ollama serve", file=sys.stderr)
        sys.exit(1)


def run_audit(
    reference_path: pathlib.Path,
    mode: str = "standard",
    with_materials: bool = False,
) -> None:
    """Run a visual audit comparing Unity screenshot to reference."""
    if not reference_path.exists():
        print(f"ERROR: reference image not found: {reference_path}", file=sys.stderr)
        sys.exit(1)

    # 1. Screenshot
    print("Taking Unity screenshot …", file=sys.stderr)
    try:
        shot_path = unity_bridge.screenshot()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Screenshot: {shot_path}", file=sys.stderr)

    images = [_encode(reference_path), _encode(shot_path)]

    # 2. Choose model and prompt
    if mode == "upgraded":
        # Use larger model with material context
        model = UPGRADED_MODEL
        material_context = _get_material_context()
        prompt = UPGRADED_AUDIT_PROMPT.format(material_context=material_context)
        print(f"Using upgraded model: {model}", file=sys.stderr)
        print(f"Material context: {len(material_context)} chars", file=sys.stderr)
    else:
        # Standard mode — try primary, fall back on OOM
        model = None  # Will be set by vram_manager
        prompt = AUDIT_PROMPT
        if with_materials:
            material_context = _get_material_context()
            prompt += f"\n\nCURRENT MATERIAL PROPERTIES:\n{material_context}"

    # 3. Call the model
    if mode == "upgraded":
        print(f"Calling {model} …", file=sys.stderr)
        result = _call_ollama(model, prompt, images, timeout=600)
        if result.startswith("OOM:"):
            print(f"[upgraded] OOM on {model}, falling back to standard mode", file=sys.stderr)
            mode = "standard"  # Fall through to standard mode below
        else:
            print(result)
            return

    # Standard mode with OOM fallback
    for oom_fallback in (False, True):
        model = vram_manager.select_model(oom_fallback=oom_fallback)
        print(f"Calling {model} …", file=sys.stderr)
        result = _call_ollama(model, prompt, images)
        if result.startswith("OOM:"):
            if not oom_fallback:
                print(f"[vram_manager] OOM on {model} — retrying with fallback", file=sys.stderr)
                continue
            print(f"ERROR: OOM even on fallback model", file=sys.stderr)
            sys.exit(1)
        print(result)
        return


def run_comparison(
    first_path: pathlib.Path,
    last_path: pathlib.Path,
    reference_path: pathlib.Path,
    iterations: int = 0,
) -> None:
    """Compare first and last screenshots to check for progress."""
    for p in (first_path, last_path, reference_path):
        if not p.exists():
            print(f"ERROR: image not found: {p}", file=sys.stderr)
            sys.exit(1)

    images = [_encode(first_path), _encode(last_path), _encode(reference_path)]
    prompt = COMPARISON_PROMPT.format(iterations=iterations)

    # Use primary model for comparison
    model = vram_manager.select_model(oom_fallback=False)
    print(f"Comparing screenshots with {model} …", file=sys.stderr)
    result = _call_ollama(model, prompt, images)
    if result.startswith("OOM:"):
        model = vram_manager.select_model(oom_fallback=True)
        result = _call_ollama(model, prompt, images)
    print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", type=pathlib.Path, default=REFERENCE_PHOTO)
    parser.add_argument("--mode", choices=["standard", "upgraded"], default="standard",
                        help="standard: qwen3-vl:8b, upgraded: qwen2.5-vl:32b + material context")
    parser.add_argument("--with-materials", action="store_true",
                        help="Include material properties in the prompt (standard mode only)")
    parser.add_argument("--compare", nargs=2, metavar=("FIRST", "LAST"),
                        help="Compare two screenshots for progress")
    parser.add_argument("--iterations", type=int, default=0,
                        help="Number of iterations (for comparison context)")
    args = parser.parse_args()

    if args.compare:
        run_comparison(
            pathlib.Path(args.compare[0]),
            pathlib.Path(args.compare[1]),
            args.ref,
            iterations=args.iterations,
        )
    else:
        run_audit(args.ref, mode=args.mode, with_materials=args.with_materials)
