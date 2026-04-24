"""
AI Avatar conversation orchestrator.

Drives the loop: greet → listen (STT) → think+speak (Claude streaming + TTS pipeline) → repeat.
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

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from log_utils import setup_logger, setup_session_logger    # noqa: E402
from ai_tools.claude.claude_client import ClaudeChatClient  # noqa: E402
from ai_tools import ChatMessage                             # noqa: E402
from aivatar_app.sentence_splitter import SentenceSplitter  # noqa: E402

logger = setup_logger("aivatar_app")

# ── Config ────────────────────────────────────────────────────────────────────

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


# ── Mic capture ───────────────────────────────────────────────────────────────

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


# ── Conversation session ──────────────────────────────────────────────────────

class ConversationSession:
    """Manages one full conversation with one Unity client."""

    def __init__(self, websocket, profile_name: str = DEFAULT_PROFILE):
        self._ws = websocket
        self._profile_name = profile_name
        self._mic = MicStreamer()
        self._stop_event = asyncio.Event()
        self._ai_client: ClaudeChatClient | None = None
        self._http: httpx.AsyncClient | None = None

        # Per-segment speak tracking (replaces the old single _done_event)
        self._pending_speaks: int = 0
        self._all_done_event = asyncio.Event()
        self._all_done_event.set()  # starts clear (nothing pending)

        # Legacy event kept for the greeting _speak() path
        self._done_event = asyncio.Event()

        # STT sentence queue — _consume_stt puts sentences here
        self._sentence_q: asyncio.Queue[str] = asyncio.Queue()

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

        stt_url = f"{STT_URL}?language=mixed"
        turn = 0
        try:
            async with httpx.AsyncClient(timeout=60.0) as http:
                self._http = http
                async with websockets.connect(stt_url, open_timeout=10) as stt_ws:
                    # Persistent mic→STT stream and STT→queue consumer
                    send_task = asyncio.create_task(self._stream_mic_to_stt(stt_ws))
                    recv_task = asyncio.create_task(self._consume_stt(stt_ws))

                    try:
                        logger.info("[session] Delivering greeting...")
                        await self._status("speaking")
                        session_log.info("Chatbot: %s", greeting)
                        await self._speak(greeting)
                        self._ai_client._history.append(
                            ChatMessage(role="assistant", content=greeting)
                        )

                        while not self._stop_event.is_set():
                            turn += 1
                            logger.info("[session] --- Turn %d: listening ---", turn)
                            await self._status("listening")
                            # Reset STT session state for a fresh turn
                            try:
                                await stt_ws.send(json.dumps({"type": "reset"}))
                            except Exception:
                                pass

                            sentence = await self._listen()
                            if sentence is None or self._stop_event.is_set():
                                logger.info("[session] Listen returned None or stop — ending")
                                break

                            logger.info("[session] Turn %d | User  : %r", turn, sentence)
                            session_log.info("User: %s", sentence)
                            await self._status("thinking")

                            reply = await self._think_and_speak(sentence, session_log, turn)
                            logger.info("[session] Turn %d | Tutor : %r", turn, reply[:200])
                            session_log.info("Chatbot: %s", reply)
                    finally:
                        send_task.cancel()
                        recv_task.cancel()
                        await asyncio.gather(send_task, recv_task, return_exceptions=True)
        finally:
            self._mic.stop()
            logger.info("[session] Ended after %d turns", turn)

    # ── STT WebSocket tasks ───────────────────────────────────────────────────

    async def _stream_mic_to_stt(self, stt_ws) -> None:
        """Forward mic PCM frames to STT WebSocket for the session lifetime."""
        while True:
            frame = await self._mic.get_frame()
            try:
                await stt_ws.send(frame)
            except websockets.exceptions.ConnectionClosed:
                break

    async def _consume_stt(self, stt_ws) -> None:
        """Read messages from STT WebSocket and route sentences to the queue."""
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
                    text = msg.get("text", "").strip()
                    if text:
                        logger.debug("[stt] Queued sentence: %r", text)
                        await self._sentence_q.put(text)
        except websockets.exceptions.ConnectionClosed:
            pass
        except asyncio.CancelledError:
            pass

    # ── Listen ────────────────────────────────────────────────────────────────

    async def _listen(self) -> str | None:
        """Wait for the next sentence from the STT consumer."""
        while not self._stop_event.is_set():
            try:
                sentence = await asyncio.wait_for(self._sentence_q.get(), timeout=0.1)
                return sentence
            except asyncio.TimeoutError:
                continue
        return None

    # ── Think + Speak (streaming pipeline) ────────────────────────────────────

    async def _think_and_speak(self, user_text: str, session_log, turn: int) -> str:
        """Stream Claude reply sentence-by-sentence, pipeline TTS, fire to Unity."""
        self._mic.pause()
        self._pending_speaks = 0
        self._all_done_event.set()  # will be cleared on first fire

        splitter = SentenceSplitter()
        reply_chunks: list[str] = []

        t_start = time.perf_counter()
        t_first_token: float | None = None
        t_first_sentence: float | None = None
        t_first_speak_sent: float | None = None

        try:
            await self._status("speaking")
            async for chunk in self._ai_client.stream_async(user_text):
                if t_first_token is None:
                    t_first_token = time.perf_counter()
                reply_chunks.append(chunk)
                for sentence in splitter.feed(chunk):
                    if t_first_sentence is None:
                        t_first_sentence = time.perf_counter()
                    sent_ok = await self._fire_tts(sentence)
                    if sent_ok and t_first_speak_sent is None:
                        t_first_speak_sent = time.perf_counter()

            if tail := splitter.flush():
                sent_ok = await self._fire_tts(tail)
                if sent_ok and t_first_speak_sent is None:
                    t_first_speak_sent = time.perf_counter()

            full_reply = "".join(reply_chunks)

            # Wait for Unity to finish playing all queued segments
            if self._pending_speaks > 0:
                timeout = max(60.0, self._pending_speaks * 30.0)
                try:
                    await asyncio.wait_for(self._all_done_event.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    logger.warning("[speak] Timed out waiting for Unity done(s)")

            t_end = time.perf_counter()
            logger.info(
                "[timing] turn=%d | first_token=+%.2fs first_sentence=+%.2fs "
                "first_speak=+%.2fs total=%.2fs",
                turn,
                (t_first_token - t_start) if t_first_token else -1,
                (t_first_sentence - t_start) if t_first_sentence else -1,
                (t_first_speak_sent - t_start) if t_first_speak_sent else -1,
                t_end - t_start,
            )
            return full_reply

        except Exception as exc:
            logger.exception("[think_and_speak] Error: %s", exc)
            await self._send_error(str(exc))
            return "Sorry, I had a little trouble. Let me try again!"
        finally:
            self._mic.resume()

    async def _fire_tts(self, text: str) -> bool:
        """Synthesize one sentence and send a speak message to Unity. Returns True on success."""
        text = text.strip()
        if not text:
            return False
        try:
            t0 = time.perf_counter()
            resp = await self._http.post(TTS_URL, json={"text": text})
            resp.raise_for_status()
            data = resp.json()
            logger.info("[speak] TTS %.2fs — %r", time.perf_counter() - t0, text[:60])

            self._pending_speaks += 1
            self._all_done_event.clear()

            await self._ws.send(json.dumps({
                "type": "speak",
                "audio_base64": data["audio_base64"],
                "sample_rate": data["sample_rate"],
                "duration_ms": data["duration_ms"],
                "viseme_events": data.get("viseme_events", []),
            }))
            return True
        except Exception as exc:
            logger.exception("[speak] TTS/fire error for %r: %s", text[:40], exc)
            return False

    # ── Greeting speak (simple, single-segment, awaits done) ─────────────────

    async def _speak(self, text: str) -> None:
        """Used for the greeting only. Synthesizes full text, waits for Unity done."""
        self._mic.pause()
        self._done_event.clear()
        try:
            t0 = time.perf_counter()
            resp = await self._http.post(TTS_URL, json={"text": text})
            resp.raise_for_status()
            data = resp.json()
            logger.info("[speak] Greeting TTS %.2fs — duration_ms=%.0f",
                        time.perf_counter() - t0, data["duration_ms"])

            await self._ws.send(json.dumps({
                "type": "speak",
                "audio_base64": data["audio_base64"],
                "sample_rate": data["sample_rate"],
                "duration_ms": data["duration_ms"],
                "viseme_events": data.get("viseme_events", []),
            }))

            timeout = max(data["duration_ms"] / 1000.0 + 10.0, 15.0)
            try:
                await asyncio.wait_for(self._done_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("[speak] Unity done timeout after %.0fs — resuming", timeout)
        except Exception as exc:
            logger.exception("[speak] Greeting TTS error: %s", exc)
            await self._send_error(str(exc))
        finally:
            self._mic.resume()

    # ── Unity message handling ────────────────────────────────────────────────

    def on_unity_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        t = msg.get("type")
        if t == "done":
            # Greeting path
            self._done_event.set()
            # Streaming pipeline path
            self._pending_speaks = max(0, self._pending_speaks - 1)
            if self._pending_speaks == 0:
                self._all_done_event.set()
            logger.debug("[unity] done received — pending_speaks=%d", self._pending_speaks)
        elif t == "stop":
            self._stop_event.set()
            self._done_event.set()
            self._all_done_event.set()

    # ── Helpers ───────────────────────────────────────────────────────────────

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
        session._all_done_event.set()
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
