#!/usr/bin/env python
"""
aivatar_ctl.py — manage Aivatar project servers (TTS, STT, orchestrator).

Usage:
    python aivatar_ctl.py --start    # start any servers not already running
    python aivatar_ctl.py --restart  # stop all, then start fresh
    python aivatar_ctl.py --exit     # gracefully stop all servers
    python aivatar_ctl.py --status   # show current status of each server
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.resolve()
PYTHON = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")

SERVICES = {
    "tts": {
        "module": "sound_engine.tts.server",
        "port": int(os.environ.get("SOUND_ENGINE_PORT", "5123")),
        "check_url": f"http://127.0.0.1:{os.environ.get('SOUND_ENGINE_PORT', '5123')}/speak",
        "check_method": "port",   # just check TCP port
        "color": "\033[36m",      # cyan
    },
    "stt": {
        "module": "sound_engine.stt.server",
        "port": int(os.environ.get("STT_PORT", "8765")),
        "check_method": "port",
        "color": "\033[35m",      # magenta
    },
    "aivatar_app": {
        "module": "aivatar_app",
        "port": int(os.environ.get("ORCHESTRATOR_PORT", "5124")),
        "check_method": "port",
        "color": "\033[33m",      # yellow
    },
}

GRACEFUL_TIMEOUT = 6   # seconds before force-kill
RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
BOLD = "\033[1m"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _color(name: str, text: str) -> str:
    return SERVICES[name]["color"] + text + RESET


def _port_in_use(port: int) -> bool:
    """Return True if something is listening on the given TCP port."""
    for conn in psutil.net_connections(kind="tcp"):
        if conn.laddr.port == port and conn.status in ("LISTEN", "ESTABLISHED"):
            return True
    return False


def _pids_for_module(module: str) -> list[int]:
    """Find PIDs of python processes running a given -m module."""
    pids = []
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = proc.info["cmdline"] or []
            if any("python" in c.lower() for c in cmd) and "-m" in cmd:
                idx = cmd.index("-m")
                if idx + 1 < len(cmd) and cmd[idx + 1] == module:
                    pids.append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
            pass
    return pids


def is_running(name: str) -> bool:
    port = SERVICES[name]["port"]
    return _port_in_use(port)


def status_line(name: str) -> str:
    running = is_running(name)
    tag = GREEN + "RUNNING" + RESET if running else RED + "STOPPED" + RESET
    port = SERVICES[name]["port"]
    return f"  {_color(name, name):<30} port {port}  [{tag}]"


# ---------------------------------------------------------------------------
# Start / stop
# ---------------------------------------------------------------------------

def start_service(name: str) -> subprocess.Popen | None:
    """Start a service. Returns Popen handle or None if already running."""
    if is_running(name):
        print(f"  {_color(name, name)} is already running — skipping.")
        return None

    module = SERVICES[name]["module"]
    log_dir = REPO_ROOT / "debug" / "logs" / name.replace("_", "_")
    log_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Starting {_color(name, name)} ...", end=" ", flush=True)
    proc = subprocess.Popen(
        [PYTHON, "-m", module],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    # Wait up to 10 s for the port to come up
    for _ in range(20):
        time.sleep(0.5)
        if is_running(name):
            print(GREEN + "OK" + RESET)
            return proc
    print(RED + "TIMEOUT (port never opened)" + RESET)
    return proc


def stop_service(name: str) -> None:
    """Gracefully stop a service; force-kill if it doesn't exit in time."""
    pids = _pids_for_module(SERVICES[name]["module"])
    if not pids and not is_running(name):
        print(f"  {_color(name, name)} is not running — skipping.")
        return

    if not pids:
        print(f"  {_color(name, name)} port is open but no matching process found — may need manual cleanup.")
        return

    print(f"  Stopping {_color(name, name)} (pid {pids}) ...", end=" ", flush=True)
    procs = []
    for pid in pids:
        try:
            p = psutil.Process(pid)
            if sys.platform == "win32":
                # CTRL_BREAK_EVENT targets a process GROUP, not a single PID —
                # sending it to a non-group-leader PID can broadcast to the current
                # console and kill aivatar_ctl itself. Use taskkill /T instead,
                # which terminates the process tree without that risk.
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                )
            else:
                p.terminate()
            procs.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    _, alive = psutil.wait_procs(procs, timeout=GRACEFUL_TIMEOUT)
    for p in alive:
        try:
            p.kill()
            print(f"(force-killed pid {p.pid}) ", end="", flush=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Wait for port to clear
    for _ in range(10):
        time.sleep(0.3)
        if not is_running(name):
            break

    print(GREEN + "stopped" + RESET)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_status() -> None:
    states = {name: is_running(name) for name in SERVICES}
    running_names = [n for n, up in states.items() if up]
    n_running = len(running_names)
    n_total = len(states)

    if n_running == n_total:
        overall = GREEN + BOLD + "Running" + RESET
    elif n_running == 0:
        overall = RED + BOLD + "Stopped" + RESET
    else:
        overall = "\033[33m" + BOLD + "Partially-running" + RESET  # yellow

    print(BOLD + "\nAivatar server status:" + RESET)
    print(f"  Overall: {overall}")
    print()
    for name in SERVICES:
        print(status_line(name))
    print()


def cmd_start() -> None:
    print(BOLD + "\nStarting Aivatar servers..." + RESET)
    # Start in dependency order: TTS → STT → orchestrator
    for name in ["tts", "stt", "aivatar_app"]:
        start_service(name)
    print()
    cmd_status()


def cmd_restart() -> None:
    print(BOLD + "\nRestarting Aivatar servers..." + RESET)
    for name in reversed(["tts", "stt", "aivatar_app"]):
        stop_service(name)
    time.sleep(1)
    for name in ["tts", "stt", "aivatar_app"]:
        start_service(name)
    print()
    cmd_status()


def cmd_exit() -> None:
    print(BOLD + "\nStopping Aivatar servers..." + RESET)
    for name in reversed(["tts", "stt", "aivatar_app"]):
        stop_service(name)
    print()
    cmd_status()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage Aivatar project servers (TTS, STT, orchestrator).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--start", action="store_true", help="Start all servers (skips already-running ones)")
    group.add_argument("--restart", action="store_true", help="Stop then start all servers")
    group.add_argument("--exit", action="store_true", help="Stop all servers gracefully")
    group.add_argument("--status", action="store_true", help="Show server status")
    args = parser.parse_args()

    if args.start:
        cmd_start()
    elif args.restart:
        cmd_restart()
    elif args.exit:
        cmd_exit()
    elif args.status:
        cmd_status()


if __name__ == "__main__":
    main()
