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

Usage:
    python audit.py [--ref PATH]
"""

from __future__ import annotations

import argparse
import base64
import pathlib
import sys

import requests
import vram_manager
import unity_bridge

# ── Paths ──────────────────────────────────────────────────────────────────

REFERENCE_PHOTO = pathlib.Path(__file__).parent / "3d_model_desired.png"

# ── Ollama ─────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"

AUDIT_PROMPT = """\
You are a 3D rendering expert. You will be shown two images:
  IMAGE 1: A reference MetaHuman character from Unreal Engine.
  IMAGE 2: The same character rendered in Unity URP.

The eyes have already been fixed and must NOT be commented on.

Focus ONLY on these three aspects:
  1. EYEBROWS — color, darkness, thickness, shape
  2. EYELASHES — thickness, darkness (should be thin and natural, not bold)
  3. HAIR — color accuracy compared to the reference

For each aspect, state whether it looks acceptable or needs improvement.
Be specific and brief (one sentence per aspect).

Then on the final line output exactly one of:
  VERDICT: DONE
  VERDICT: NEEDS CHANGES
"""


def _encode(path: pathlib.Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def run_audit(reference_path: pathlib.Path) -> None:
    if not reference_path.exists():
        print(f"ERROR: reference image not found: {reference_path}", file=sys.stderr)
        sys.exit(1)

    # 1. Screenshot first (no GPU needed)
    print("Taking Unity screenshot …", file=sys.stderr)
    try:
        shot_path = unity_bridge.screenshot()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Screenshot: {shot_path}", file=sys.stderr)

    images = [_encode(reference_path), _encode(shot_path)]
    payload_base = {
        "messages": [{"role": "user", "content": AUDIT_PROMPT, "images": images}],
        "stream": False,
        "think": False,  # disable chain-of-thought for qwen3 models
        "options": {"temperature": 0.1, "num_predict": 512},
    }

    # 2. Try primary model; fall back to fallback only on OOM
    for oom_fallback in (False, True):
        model = vram_manager.select_model(oom_fallback=oom_fallback)
        print(f"Calling {model} …", file=sys.stderr)
        try:
            resp = requests.post(OLLAMA_URL, json={**payload_base, "model": model}, timeout=180)
            resp.raise_for_status()
            # Ollama surfaces OOM in the response error field
            body = resp.json()
            if "error" in body:
                err = body["error"].lower()
                if "out of memory" in err or "oom" in err:
                    if not oom_fallback:
                        print(f"[vram_manager] OOM on {model} — retrying with fallback", file=sys.stderr)
                        continue
                print(f"ERROR from Ollama: {body['error']}", file=sys.stderr)
                sys.exit(1)
            print(body["message"]["content"])
            return
        except requests.exceptions.ConnectionError:
            print("ERROR: Cannot connect to Ollama. Run: ollama serve", file=sys.stderr)
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            if "out of memory" in str(e).lower() and not oom_fallback:
                print(f"[vram_manager] OOM on {model} — retrying with fallback", file=sys.stderr)
                continue
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", type=pathlib.Path, default=REFERENCE_PHOTO)
    args = parser.parse_args()
    run_audit(args.ref)
