"""
approach_tracker.py — Tracks which improvement approach is active and manages
iteration counting + screenshot comparison.

State is persisted to a JSON file so it survives across conversation restarts.

The 3d-model-improver skill uses this to:
1. Know which approach to use for the current iteration
2. Count iterations per approach
3. Store the first screenshot of each approach for before/after comparison
4. Switch to the next approach when the current one fails after N iterations
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional

_STATE_FILE = pathlib.Path(__file__).parent / "approach_state.json"
_SCREENSHOTS_DIR = pathlib.Path(__file__).parent / "approach_screenshots"

# Ordered list of approaches to try
APPROACHES = [
    {
        "id": "csharp_fixer",
        "name": "C# Material Fixer (deterministic)",
        "description": "Fix material shader keywords, render queues, surface types, alpha clipping via Unity's Material API. Addresses root cause: shader keywords were disabled.",
        "max_iterations": 10,  # Deterministic fix — shouldn't need many iterations
    },
    {
        "id": "texture_surgery",
        "name": "Texture Surgery (Pillow)",
        "description": "Direct pixel-level manipulation of textures: thin eyelash alpha channel, paint eyebrows onto face texture, adjust hair texture contrast.",
        "max_iterations": 15,
    },
    {
        "id": "upgraded_ai",
        "name": "Upgraded AI (qwen2.5-vl:32b) + Full Material Context",
        "description": "Use qwen2.5-vl:32b (4x larger model) with full material property dumps sent alongside screenshots. Enhanced mat_editor can set shader keywords.",
        "max_iterations": 60,
    },
]


@dataclass
class ApproachState:
    current_approach_index: int = 0
    iteration_count: int = 0
    first_screenshot: Optional[str] = None
    last_screenshot: Optional[str] = None
    approach_history: list = field(default_factory=list)

    def save(self) -> None:
        _STATE_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> "ApproachState":
        if _STATE_FILE.exists():
            try:
                data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
                return cls(**{k: v for k, v in data.items()
                             if k in cls.__dataclass_fields__})
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    @property
    def current_approach(self) -> dict:
        if self.current_approach_index < len(APPROACHES):
            return APPROACHES[self.current_approach_index]
        return APPROACHES[-1]  # Stay on last approach

    @property
    def max_iterations(self) -> int:
        return self.current_approach["max_iterations"]

    @property
    def should_switch(self) -> bool:
        return self.iteration_count >= self.max_iterations

    @property
    def all_approaches_exhausted(self) -> bool:
        return self.current_approach_index >= len(APPROACHES) - 1 and self.should_switch


def get_state() -> ApproachState:
    """Load the current approach state."""
    return ApproachState.load()


def increment_iteration(screenshot_path: str | None = None) -> ApproachState:
    """Increment the iteration counter and optionally store screenshot path."""
    state = ApproachState.load()
    state.iteration_count += 1

    if screenshot_path:
        if state.first_screenshot is None:
            state.first_screenshot = screenshot_path
            # Also save a copy of the first screenshot
            _SCREENSHOTS_DIR.mkdir(exist_ok=True)
            approach_id = state.current_approach["id"]
            first_copy = _SCREENSHOTS_DIR / f"{approach_id}_first.png"
            try:
                shutil.copy2(screenshot_path, first_copy)
            except Exception:
                pass
        state.last_screenshot = screenshot_path

    state.save()
    return state


def switch_to_next_approach(reason: str = "") -> ApproachState:
    """
    Switch to the next approach. Records history of what was tried.
    Returns the updated state.
    """
    state = ApproachState.load()

    # Record what we just finished
    state.approach_history.append({
        "approach": state.current_approach["id"],
        "iterations": state.iteration_count,
        "first_screenshot": state.first_screenshot,
        "last_screenshot": state.last_screenshot,
        "reason": reason,
    })

    # Move to next
    state.current_approach_index += 1
    state.iteration_count = 0
    state.first_screenshot = None
    state.last_screenshot = None

    state.save()

    if state.current_approach_index < len(APPROACHES):
        approach = state.current_approach
        print(f"[approach_tracker] Switched to approach {state.current_approach_index + 1}/{len(APPROACHES)}: "
              f"{approach['name']}", file=sys.stderr)
    else:
        print("[approach_tracker] All approaches exhausted!", file=sys.stderr)

    return state


def reset() -> ApproachState:
    """Reset to the first approach (start fresh)."""
    state = ApproachState()
    state.save()
    return state


def get_comparison_screenshots() -> tuple[str | None, str | None]:
    """Return (first_screenshot, last_screenshot) paths for the current approach."""
    state = ApproachState.load()
    return state.first_screenshot, state.last_screenshot


def get_status_summary() -> str:
    """Return a human-readable summary of the current state."""
    state = ApproachState.load()
    approach = state.current_approach
    lines = [
        f"Current approach: {approach['name']} ({state.current_approach_index + 1}/{len(APPROACHES)})",
        f"Iteration: {state.iteration_count}/{approach['max_iterations']}",
    ]
    if state.approach_history:
        lines.append(f"Previously tried: {len(state.approach_history)} approaches")
        for h in state.approach_history:
            lines.append(f"  - {h['approach']}: {h['iterations']} iterations, reason: {h.get('reason', 'N/A')}")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("status")
    sub.add_parser("reset")
    sub.add_parser("next")

    args = parser.parse_args()
    if args.cmd == "status":
        print(get_status_summary())
    elif args.cmd == "reset":
        reset()
        print("Reset to first approach.")
    elif args.cmd == "next":
        switch_to_next_approach("manual switch")
        print(get_status_summary())
    else:
        print(get_status_summary())
