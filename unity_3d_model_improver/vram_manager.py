"""
VRAM manager: always uses the primary model; falls back only on actual OOM.

Ollama manages its own VRAM and unloads models automatically, so proactive
free-memory checks just cause unnecessary fallbacks when a previous model run
is still resident. Instead we always attempt the primary model and let the
caller catch OOM errors and switch to the fallback for that session.

Usage:
    python vram_manager.py           # prints current free VRAM (info only)
    from vram_manager import PRIMARY_MODEL, FALLBACK_MODEL, free_vram_gb
"""

from __future__ import annotations
import subprocess
import sys

PRIMARY_MODEL  = "qwen3-vl:8b"     # Qwen3 vision-language model, ~6GB VRAM
FALLBACK_MODEL = "qwen2.5vl:7b"   # fallback vision model, ~5GB VRAM


def free_vram_gb() -> float:
    """Return free dedicated VRAM in gigabytes (informational only)."""
    try:
        import pynvml  # nvidia-ml-py exposes the pynvml namespace
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        pynvml.nvmlShutdown()
        return info.free / (1024 ** 3)
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return float(result.stdout.strip().splitlines()[0]) / 1024.0
    except Exception:
        pass

    return 0.0


def select_model(oom_fallback: bool = False) -> str:
    """Return the model to use.

    Always returns PRIMARY_MODEL unless oom_fallback=True, in which case
    FALLBACK_MODEL is returned for the rest of the session.
    """
    free = free_vram_gb()
    model = FALLBACK_MODEL if oom_fallback else PRIMARY_MODEL
    print(f"[vram_manager] Free VRAM: {free:.1f} GB  ->  model: {model}")
    return model


if __name__ == "__main__":
    free = free_vram_gb()
    print(f"Free VRAM: {free:.1f} GB")
    print(f"Will use:  {PRIMARY_MODEL} (always, unless OOM occurs)")
