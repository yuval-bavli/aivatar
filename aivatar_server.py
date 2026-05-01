#!/usr/bin/env python
"""
aivatar_server.py — single-process master server for all Aivatar services.

Runs TTS (5123), STT (8765), and the orchestrator (5124) in one process.
A management HTTP endpoint is available on port 5125 (/status, /health).

Usage:
    .venv/Scripts/python aivatar_server.py
    .venv/Scripts/python aivatar_server.py --no-stt   # skip STT (no GPU required)

Environment overrides (same as individual servers):
    SOUND_ENGINE_PORT   TTS port   (default 5123)
    STT_PORT            STT port   (default 8765)
    ORCHESTRATOR_PORT   orch port  (default 5124)
    MASTER_PORT         mgmt port  (default 5125)
    AVATAR_PROFILE      profile folder (default english_tutor_heb)
"""
import argparse
import asyncio
import json
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

# Set up master logger first so all service logs in this process share one file.
from log_utils import setup_logger  # noqa: E402
logger = setup_logger("master_server")

TTS_PORT  = int(os.environ.get("SOUND_ENGINE_PORT", "5123"))
STT_PORT  = int(os.environ.get("STT_PORT",          "8765"))
ORCH_PORT = int(os.environ.get("ORCHESTRATOR_PORT", "5124"))
MGMT_PORT = int(os.environ.get("MASTER_PORT",       "5125"))

_START_TIME = time.monotonic()


# ---------------------------------------------------------------------------
# Port probe helper
# ---------------------------------------------------------------------------

def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0


# ---------------------------------------------------------------------------
# TTS — blocking HTTPServer in a daemon thread
# ---------------------------------------------------------------------------

def _run_tts() -> None:
    from sound_engine.tts.server import SpeechHandler
    logger.info("[tts] Loading synthesizer and aligners…")
    SpeechHandler._load_aligners()
    SpeechHandler.get_synthesizer()
    server = HTTPServer(("127.0.0.1", TTS_PORT), SpeechHandler)
    logger.info("[tts] Ready → http://127.0.0.1:%d/speak", TTS_PORT)
    server.serve_forever()


# ---------------------------------------------------------------------------
# STT — uvicorn/FastAPI in a daemon thread (owns its own event loop)
# ---------------------------------------------------------------------------

def _run_stt() -> None:
    import uvicorn
    from sound_engine.stt.server import app as stt_app
    logger.info("[stt] Starting uvicorn on ws://127.0.0.1:%d", STT_PORT)
    config = uvicorn.Config(
        stt_app,
        host="127.0.0.1",
        port=STT_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    server.run()  # blocks; creates and owns its own asyncio event loop


# ---------------------------------------------------------------------------
# Management endpoint — lightweight status/health in a daemon thread
# ---------------------------------------------------------------------------

class _MgmtHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in ("/status", "/health"):
            self.send_error(404)
            return
        body = json.dumps({
            "status": "ok",
            "uptime_s": round(time.monotonic() - _START_TIME),
            "services": {
                "tts":          {"port": TTS_PORT,  "running": _port_open(TTS_PORT)},
                "stt":          {"port": STT_PORT,  "running": _port_open(STT_PORT)},
                "orchestrator": {"port": ORCH_PORT, "running": _port_open(ORCH_PORT)},
                "management":   {"port": MGMT_PORT, "running": True},
            },
        }, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        pass


def _run_mgmt() -> None:
    server = HTTPServer(("127.0.0.1", MGMT_PORT), _MgmtHandler)
    server.serve_forever()


# ---------------------------------------------------------------------------
# Main coroutine — starts daemon threads, then runs orchestrator
# ---------------------------------------------------------------------------

async def _amain(enable_stt: bool) -> None:
    from aivatar_app.orchestrator import run_server

    threading.Thread(target=_run_mgmt, name="mgmt", daemon=True).start()
    logger.info("[mgmt] Management endpoint → http://127.0.0.1:%d/status", MGMT_PORT)

    threading.Thread(target=_run_tts, name="tts", daemon=True).start()

    if enable_stt:
        threading.Thread(target=_run_stt, name="stt", daemon=True).start()
    else:
        logger.info("[stt] Skipped (--no-stt)")

    # Orchestrator owns the main event loop and blocks until Ctrl+C / SIGINT.
    await run_server()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aivatar master server — TTS + STT + orchestrator in one process.",
    )
    parser.add_argument(
        "--no-stt", action="store_true",
        help="Skip the STT server (removes CUDA/GPU requirement)",
    )
    args = parser.parse_args()

    logger.info("=== Aivatar master server starting ===")
    logger.info(
        "ports — TTS:%d  STT:%d  orchestrator:%d  management:%d",
        TTS_PORT, STT_PORT, ORCH_PORT, MGMT_PORT,
    )

    try:
        asyncio.run(_amain(enable_stt=not args.no_stt))
    except KeyboardInterrupt:
        logger.info("=== Aivatar master server stopped ===")


if __name__ == "__main__":
    main()
