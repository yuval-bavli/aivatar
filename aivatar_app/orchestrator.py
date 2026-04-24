"""
AI Avatar conversation orchestrator.

Drives the loop: greet → listen (STT) → think (Claude) → speak (TTS+Unity) → repeat.
Unity connects as a WebSocket client; this process is the server.

Run:
    .venv/Scripts/python -m aivatar_app

Requires TTS server (port 5123) and STT server (port 8765) to be running first.

Environment overrides:
    TTS_URL            default: http://127.0.0.1:5123/speak
    STT_URL            default: ws://127.0.0.1:8765/ws/transcribe
    ORCHESTRATOR_PORT  default: 5124
    AVATAR_PROFILE     default: english_tutor_heb
"""
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx
import sounddevice as sd
import websockets
import websockets.exceptions

# Ensure repo root is on sys.path so ai_tools and log_utils are importable
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from log_utils import setup_logger, setup_session_logger    # noqa: E402
from ai_tools.claude.claude_client import ClaudeChatClient  # noqa: E402
from ai_tools import ChatMessage  # noqa: E402

logger = setup_logger("aivatar_app")

# ── Config ───────────────────────────────────────────────────────────────────

SAMPLE_RATE = 16_000
CHANNELS = 1
CHUNK_MS = 64
DTYPE = "int16"

TTS_URL = os.environ.get("TTS_URL", "http://127.0.0.1:5123/speak")
STT_URL = os.environ.get("STT_URL", "ws://127.0.0.1:8765/ws/transcribe")
ORCHESTRATOR_HOST = "127.0.0.1"
ORCHESTRATOR_PORT = int(os.environ.get("ORCHESTRATOR_PORT", "5124"))
DEFAULT_PROFILE = os.environ.get("AVATAR_PROFILE", "english_tutor_heb")

PROFILES_DIR = _REPO_ROOT / "profiles"


# ── Mic capture ──────────────────────────────────────────────────────────────

class MicStreamer:
    """Captures mic audio and puts 16kHz s16le mono PCM frames into an asyncio Queue."""

    def __init__(self, device=None):
        self._q: asyncio.Queue[bytes] = asyncio.Queue()
        self._stream = None
        self._paused = False
        self._device = device
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        chunk_samples = int(SAMPLE_RATE * CHUNK_MS / 1000)

        def _cb(indata, frames, time, status):
            if status:
                logger.warning("[mic] %s", status)
            if not self._paused and self._loop is not None:
                asyncio.run_coroutine_threadsafe(
                    self._q.put(bytes(indata[:, 0])), self._loop
                )

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=chunk_samples,
            device=self._device,
            callback=_cb,
        )
        self._stream.start()
        logger.info("[mic] Capture started (device=%s)", self._device or "default")

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        # drain frames accumulated during pause to avoid replaying avatar's own voice
        drained = 0
        while not self._q.empty():
            try:
                self._q.get_nowait()
                drained += 1
            except Exception:
                break
        if drained:
            logger.debug("[mic] Drained %d echo frames on resume", drained)
        self._paused = False

    def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    async def get_frame(self) -> bytes:
        return await self._q.get()


# ── Conversation session ─────────────────────────────────────────────────────

class ConversationSession:
    """Manages one full conversation with one Unity client."""

    def __init__(self, websocket, profile_name: str = DEFAULT_PROFILE):
        self._ws = websocket
        self._profile_name = profile_name
        self._mic = MicStreamer()
        self._done_event = asyncio.Event()
        self._stop_event = asyncio.Event()
        self._ai_client: ClaudeChatClient | None = None
        self._http: httpx.AsyncClient | None = None

    async def run(self) -> None:
        profile_dir = PROFILES_DIR / self._profile_name
        if not profile_dir.exists():
            raise FileNotFoundError(f"Profile not found: {profile_dir}")

        system_prompt = (profile_dir / "system_prompt.md").read_text(encoding="utf-8")
        greeting_file = profile_dir / "greeting.txt"
        greeting = (
            greeting_file.read_text(encoding="utf-8").strip()
            if greeting_file.exists()
            else "Hi! I'm Sunny, your English teacher! Can you say hello?"
        )

        self._ai_client = ClaudeChatClient(system_prompt=system_prompt)
        logger.info("[session] Profile loaded: %s", self._profile_name)
        logger.info("[session] Greeting: %r", greeting[:80])

        session_log = setup_session_logger()

        loop = asyncio.get_event_loop()
        self._mic.start(loop)

        turn = 0
        try:
            async with httpx.AsyncClient(timeout=60.0) as http:
                self._http = http

                logger.info("[session] Delivering greeting...")
                await self._status("speaking")
                session_log.info("Chatbot: %s", greeting)
                await self._speak(greeting)
                # Seed history so Claude knows it already introduced itself
                self._ai_client._history.append(
                    ChatMessage(role="assistant", content=greeting)
                )

                while not self._stop_event.is_set():
                    turn += 1
                    logger.info("[session] --- Turn %d: listening ---", turn)
                    await self._status("listening")
                    sentence = await self._listen()
                    if sentence is None or self._stop_event.is_set():
                        logger.info("[session] Listen returned None or stop — ending loop")
                        break

                    logger.info("[session] Turn %d | User  : %r", turn, sentence)
                    session_log.info("User: %s", sentence)
                    await self._status("thinking")
                    reply = await self._think(sentence)
                    logger.info("[session] Turn %d | Tutor : %r", turn, reply[:200])
                    session_log.info("Chatbot: %s", reply)

                    await self._status("speaking")
                    await self._speak(reply)
        finally:
            self._mic.stop()
            logger.info("[session] Ended after %d turns", turn)

    # ── Core steps ───────────────────────────────────────────────────────────

    async def _speak(self, text: str) -> None:
        """Send text -> TTS, push speak message to Unity, wait for done."""
        self._mic.pause()
        self._done_event.clear()
        preview = text[:80] + ("..." if len(text) > 80 else "")
        logger.debug("[speak] Requesting TTS for: %r", preview)
        try:
            t0 = time.perf_counter()
            resp = await self._http.post(TTS_URL, json={"text": text})
            resp.raise_for_status()
            data = resp.json()
            tts_elapsed = time.perf_counter() - t0
            logger.info("[speak] TTS ok — duration_ms=%.0f visemes=%d tts_elapsed=%.2fs",
                        data["duration_ms"], len(data.get("viseme_events", [])), tts_elapsed)

            await self._ws.send(json.dumps({
                "type": "speak",
                "audio_base64": data["audio_base64"],
                "sample_rate": data["sample_rate"],
                "duration_ms": data["duration_ms"],
                "viseme_events": data.get("viseme_events", []),
            }))
            logger.debug("[speak] Sent to Unity — waiting for 'done'")

            # Wait for Unity "done" with a safety timeout
            timeout = max(data["duration_ms"] / 1000.0 + 10.0, 15.0)
            try:
                await asyncio.wait_for(self._done_event.wait(), timeout=timeout)
                logger.debug("[speak] Unity signalled done")
            except asyncio.TimeoutError:
                logger.warning("[speak] Unity done timeout after %.0fs — resuming", timeout)
        except Exception as exc:
            logger.exception("[speak] TTS/speak error: %s", exc)
            await self._send_error(str(exc))
        finally:
            self._mic.resume()

    async def _listen(self) -> str | None:
        """Stream mic to STT server, return the first complete sentence."""
        stt_url = f"{STT_URL}?language=mixed"
        try:
            async with websockets.connect(stt_url, open_timeout=10) as stt_ws:
                send_task = asyncio.create_task(self._stream_mic(stt_ws))
                sentence: str | None = None
                try:
                    async for raw in stt_ws:
                        if isinstance(raw, bytes):
                            continue
                        if self._stop_event.is_set():
                            break
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if msg.get("type") == "sentence":
                            sentence = msg.get("text", "").strip()
                            break
                finally:
                    send_task.cancel()
                    try:
                        await send_task
                    except asyncio.CancelledError:
                        pass
                return sentence
        except Exception as exc:
            logger.error("[session] STT listen error: %s", exc)
            return None

    async def _stream_mic(self, stt_ws) -> None:
        """Forward mic frames to STT WebSocket until cancelled."""
        while True:
            frame = await self._mic.get_frame()
            try:
                await stt_ws.send(frame)
            except websockets.exceptions.ConnectionClosed:
                break

    async def _think(self, text: str) -> str:
        """Send user text to Claude, return reply."""
        logger.debug("[think] Sending to Claude: %r", text[:120])
        t0 = time.perf_counter()
        try:
            response = await self._ai_client.send_async(text)
            elapsed = time.perf_counter() - t0
            logger.info("[think] Claude replied in %.2fs — tokens_in=%s tokens_out=%s",
                        elapsed,
                        response.usage.get("input_tokens", "?"),
                        response.usage.get("output_tokens", "?"))
            logger.debug("[think] Reply: %r", response.content[:200])
            return response.content
        except Exception as exc:
            logger.exception("[think] Claude error after %.2fs: %s", time.perf_counter() - t0, exc)
            return "Sorry, I had a little trouble. Let me try again!"

    # ── Unity message handling ────────────────────────────────────────────────

    def on_unity_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        t = msg.get("type")
        if t == "done":
            self._done_event.set()
        elif t == "stop":
            self._stop_event.set()
            self._done_event.set()

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _status(self, state: str) -> None:
        try:
            await self._ws.send(json.dumps({"type": "status", "state": state}))
        except Exception:
            pass

    async def _send_error(self, message: str) -> None:
        try:
            await self._ws.send(json.dumps({"type": "error", "message": message}))
        except Exception:
            pass


# ── WebSocket server ──────────────────────────────────────────────────────────

async def _handle_client(websocket) -> None:
    addr = getattr(websocket, "remote_address", "unknown")
    logger.info("[orchestrator] Unity connected from %s", addr)
    session = ConversationSession(websocket)
    run_task = asyncio.create_task(session.run())

    try:
        async for raw in websocket:
            if isinstance(raw, bytes):
                continue
            logger.debug("[orchestrator] Unity msg: %s", raw[:120])
            session.on_unity_message(raw)
    except websockets.exceptions.ConnectionClosed:
        logger.info("[orchestrator] Unity WebSocket closed")
    except Exception as exc:
        logger.exception("[orchestrator] Unexpected error in client handler: %s", exc)
    finally:
        session._stop_event.set()
        session._done_event.set()
        run_task.cancel()
        try:
            await run_task
        except asyncio.CancelledError:
            pass
        logger.info("[orchestrator] Unity disconnected from %s", addr)


async def run_server() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("[orchestrator] Listening on ws://%s:%d", ORCHESTRATOR_HOST, ORCHESTRATOR_PORT)
    logger.info("[orchestrator] Waiting for Unity to connect …")
    logger.info("[orchestrator] TTS → %s  |  STT → %s", TTS_URL, STT_URL)

    async with websockets.serve(_handle_client, ORCHESTRATOR_HOST, ORCHESTRATOR_PORT):
        await asyncio.Future()  # run until Ctrl+C
