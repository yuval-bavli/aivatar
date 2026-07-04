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
import websockets
import websockets.exceptions

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from log_utils import setup_logger, setup_session_logger    # noqa: E402
from ai_tools.claude.claude_client import ClaudeChatClient  # noqa: E402
from ai_tools import ChatMessage                             # noqa: E402
from aivatar_app.sentence_splitter import SentenceSplitter  # noqa: E402
from aivatar_app.session_store import Session, SessionStore  # noqa: E402

logger = setup_logger("aivatar_app")

# ── Config ────────────────────────────────────────────────────────────────────

TTS_URL = os.environ.get("TTS_URL", "http://127.0.0.1:5123/speak")
STT_URL = os.environ.get("STT_URL", "ws://127.0.0.1:8765/ws/transcribe")
ORCHESTRATOR_HOST = os.environ.get("ORCHESTRATOR_HOST", "127.0.0.1")
ORCHESTRATOR_PORT = int(os.environ.get("ORCHESTRATOR_PORT", "5124"))
DEFAULT_PROFILE = os.environ.get("AVATAR_PROFILE", "english_tutor_heb")
STT_VAD_SILENCE_MS = int(os.environ.get("STT_VAD_SILENCE_MS", "800"))

PROFILES_DIR = _REPO_ROOT / "profiles"
MAX_HISTORY_TOKENS = int(os.environ.get("MAX_HISTORY_TOKENS", "30000"))
SESSIONS_DIR = Path(os.environ.get("SESSIONS_DIR", str(_REPO_ROOT / "sessions")))

_TURN_END = object()  # sentinel enqueued on the TTS queue marking end of one turn's sentences
_WORKER_STOP = object()  # sentinel to shut down the TTS worker task


async def _single_chunk_stream(text: str):
    """Wrap a plain string as a one-shot async chunk iterator (fallback greeting path)."""
    yield text


# ── Conversation session ──────────────────────────────────────────────────────

class ConversationSession:
    """Manages one full conversation with one Unity client."""

    def __init__(self, websocket, profile_name: str = DEFAULT_PROFILE):
        self._ws = websocket
        self._profile_name = profile_name
        self._audio_q: asyncio.Queue[bytes] = asyncio.Queue()
        self._stop_event = asyncio.Event()
        self._ai_client: ClaudeChatClient | None = None
        self._http: httpx.AsyncClient | None = None
        self._store = SessionStore(SESSIONS_DIR)
        self._session: Session | None = None

        # Per-segment speak tracking — decremented as Unity acks each queued segment
        self._pending_speaks: int = 0
        self._all_done_event = asyncio.Event()
        self._all_done_event.set()  # starts clear (nothing pending)

        # STT sentence queue — _consume_stt puts sentences here
        self._sentence_q: asyncio.Queue[str] = asyncio.Queue()

        # STT connection, owned by _stt_supervisor — None while disconnected/reconnecting
        self._stt_ws = None
        self._stt_ready_event = asyncio.Event()

        # TTS pipeline: producer (LLM stream) -> queue -> single worker -> Unity.
        # Decouples TTS synthesis latency from LLM token generation.
        self._tts_q: asyncio.Queue = asyncio.Queue()
        self._turn_drained_event = asyncio.Event()
        self._speaking_started = False
        self._first_speak_sent_ts: float | None = None

        # Background history summarization, kicked off between turns
        self._summarize_task: asyncio.Task | None = None

    async def run(self) -> None:
        profile_dir = PROFILES_DIR / self._profile_name
        if not profile_dir.exists():
            raise FileNotFoundError(f"Profile not found: {profile_dir}")

        system_prompt = (profile_dir / "system_prompt.md").read_text(encoding="utf-8")
        lesson_files = sorted(profile_dir.glob("lesson_*.md"))
        if lesson_files:
            lessons_block = "\n\n".join(
                f"## {f.stem}\n\n{f.read_text(encoding='utf-8').strip()}"
                for f in lesson_files
            )
            system_prompt += "\n\n# Lesson Materials\n\n" + lessons_block
            logger.info("[session] Injected %d lesson file(s) into system prompt", len(lesson_files))
        greeting_file = profile_dir / "greeting.txt"

        fallback_greeting = (
            greeting_file.read_text(encoding="utf-8").strip()
            if greeting_file.exists()
            else "Hi! I'm Sunny, your English teacher! Can you say hello? Say: Hello!"
        )

        prior = self._store.latest_for_profile(self._profile_name)
        if prior and prior.messages:
            logger.info("[session] Resuming session %s (%d messages)", prior.session_id, len(prior.messages))
            self._session = prior
            self._ai_client = ClaudeChatClient(
                system_prompt=system_prompt,
                summary_context=prior.summary or "",
            )
            self._ai_client.set_history([
                ChatMessage(role=m["role"], content=m["content"])
                for m in prior.messages
            ])
        else:
            logger.info("[session] Starting new session for profile %s", self._profile_name)
            self._session = self._store.new(self._profile_name)
            self._ai_client = ClaudeChatClient(system_prompt=system_prompt)

        logger.info("[session] Profile loaded: %s", self._profile_name)

        session_log = setup_session_logger()

        stt_url = f"{STT_URL}?language=mixed"
        turn = 0
        try:
            async with httpx.AsyncClient(timeout=60.0) as http:
                self._http = http

                worker_task = asyncio.create_task(self._tts_worker())
                stt_task = asyncio.create_task(self._stt_supervisor(stt_url))

                try:
                    await self._stt_ready_event.wait()
                    if self._stop_event.is_set():
                        return  # initial connect failed — error already sent by the supervisor

                    if prior and prior.messages:
                        logger.info("[session] Generating welcome-back greeting...")
                        try:
                            greeting = await self._speak_turn(
                                self._welcome_back_stream(system_prompt), "greeting")
                        except Exception as exc:
                            logger.warning("[session] Welcome-back streaming failed (%s) — using fallback", exc)
                            greeting = await self._speak_turn(
                                _single_chunk_stream(
                                    "Welcome back! Let's continue where we left off. Can you say hello?"),
                                "greeting")
                    else:
                        logger.info("[session] Generating new-session greeting...")
                        try:
                            greeting = await self._speak_turn(
                                self._new_greeting_stream(system_prompt), "greeting")
                        except Exception as exc:
                            logger.warning("[session] New-session greeting streaming failed (%s) — using fallback", exc)
                            greeting = await self._speak_turn(
                                _single_chunk_stream(fallback_greeting), "greeting")

                    session_log.info("Chatbot: %s", greeting)
                    self._ai_client._history.append(
                        ChatMessage(role="assistant", content=greeting)
                    )
                    self._session.messages = [
                        {"role": m.role, "content": m.content}
                        for m in self._ai_client._history
                    ]
                    self._store.save(self._session)

                    while not self._stop_event.is_set():
                        turn += 1
                        logger.info("[session] --- Turn %d: listening ---", turn)
                        await self._status("listening")
                        # Drain audio frames that arrived during speaking to avoid echo
                        drained = 0
                        while not self._audio_q.empty():
                            try:
                                self._audio_q.get_nowait()
                                drained += 1
                            except asyncio.QueueEmpty:
                                break
                        if drained:
                            logger.debug("[session] Drained %d stale audio frames", drained)
                        # Reset STT session state for a fresh turn
                        try:
                            if self._stt_ws is not None:
                                await self._stt_ws.send(json.dumps({"type": "reset"}))
                        except Exception:
                            pass

                        sentence = await self._listen()
                        if sentence is None or self._stop_event.is_set():
                            logger.info("[session] Listen returned None or stop — ending")
                            break

                        logger.info("[session] Turn %d | User  : %r", turn, sentence)
                        session_log.info("User: %s", sentence)
                        await self._status("thinking")
                        await self._send_transcript(sentence)

                        reply = await self._think_and_speak(sentence, session_log, turn)
                        logger.info("[session] Turn %d | Tutor : %r", turn, reply[:200])
                        session_log.info("Chatbot: %s", reply)
                        await self._save_session_state()
                        if self._should_summarize() and (
                                self._summarize_task is None or self._summarize_task.done()):
                            logger.info("[session] Kicking off background summarization")
                            self._summarize_task = asyncio.create_task(
                                self._summarize_and_compact(system_prompt))
                finally:
                    self._stop_event.set()
                    stt_task.cancel()
                    self._tts_q.put_nowait(_WORKER_STOP)
                    cleanup_tasks = [stt_task, worker_task]
                    if self._summarize_task is not None:
                        self._summarize_task.cancel()
                        cleanup_tasks.append(self._summarize_task)
                    await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        finally:
            logger.info("[session] Ended after %d turns", turn)

    # ── STT connection supervisor (connects, reconnects with backoff) ────────

    async def _stt_supervisor(self, stt_url: str) -> None:
        """Owns the STT connection for the session's lifetime. Forwards mic audio and
        consumes STT events via two child tasks; if the connection drops mid-session,
        reconnects with exponential backoff instead of leaving _listen() wedged forever."""
        stt_ws = await self._initial_stt_connect(stt_url)
        if stt_ws is None:
            return  # error already sent, _stop_event already set

        while not self._stop_event.is_set():
            self._stt_ws = stt_ws
            try:
                await stt_ws.send(json.dumps({
                    "type": "config",
                    "vad_silence_ms": STT_VAD_SILENCE_MS,
                }))
            except Exception:
                pass
            self._stt_ready_event.set()

            send_task = asyncio.create_task(self._stream_mic_to_stt(stt_ws))
            recv_task = asyncio.create_task(self._consume_stt(stt_ws))
            try:
                # try/finally here (not just after) so that if this task itself is
                # cancelled mid-wait (session ending), send_task/recv_task and the
                # socket are still cleaned up instead of leaking.
                await asyncio.wait({send_task, recv_task}, return_when=asyncio.FIRST_COMPLETED)
            finally:
                send_task.cancel()
                recv_task.cancel()
                await asyncio.gather(send_task, recv_task, return_exceptions=True)
                try:
                    await stt_ws.close()
                except Exception:
                    pass
                self._stt_ws = None

            if self._stop_event.is_set():
                return

            logger.warning("[stt] Connection lost mid-session — reconnecting")
            await self._status("reconnecting")
            stt_ws = await self._reconnect_stt(stt_url)
            if stt_ws is None:
                return  # gave up after 60s — error already sent, _stop_event already set

    async def _initial_stt_connect(self, stt_url: str):
        """First connection at session start. Under Docker Compose, aivatar_app's
        depends_on/healthcheck already waits for STT to report ready before this
        container even starts, so this is mostly a safety net for bare-metal dev
        runs (`.venv/Scripts/python -m aivatar_app` without Compose gating)."""
        for attempt in range(30):
            try:
                return await websockets.connect(stt_url, open_timeout=5)
            except Exception:
                if attempt == 0:
                    logger.info("[session] Waiting for STT server to be ready (model loading)...")
                await asyncio.sleep(2)
        logger.error("[session] STT unreachable after 60s — aborting session")
        await self._send_error("STT server not available")
        self._stop_event.set()
        self._stt_ready_event.set()  # unblock run()'s wait so it can see stop_event and exit
        return None

    async def _reconnect_stt(self, stt_url: str):
        """Reconnect with exponential backoff (1s, 2s, 4s, ... capped at 10s), giving
        up (and ending the session) after 60s of failed attempts."""
        start = time.perf_counter()
        delay = 1.0
        while not self._stop_event.is_set():
            try:
                return await websockets.connect(stt_url, open_timeout=10)
            except Exception:
                if time.perf_counter() - start > 60.0:
                    logger.error("[stt] Reconnect failed for 60s — ending session")
                    await self._send_error("STT server unreachable")
                    self._stop_event.set()
                    return None
                await asyncio.sleep(delay)
                delay = min(delay * 2, 10.0)
        return None

    async def _stream_mic_to_stt(self, stt_ws) -> None:
        """Forward PCM frames received from Unity to the STT WebSocket."""
        while True:
            frame = await self._audio_q.get()
            try:
                await stt_ws.send(frame)
            except websockets.exceptions.ConnectionClosed:
                break

    def on_audio_frame(self, data: bytes) -> None:
        """Called by the WebSocket handler when Unity sends a binary audio frame."""
        try:
            self._audio_q.put_nowait(data)
        except asyncio.QueueFull:
            pass

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
                elif msg.get("type") == "vad_event" and msg.get("event") == "speech_start":
                    # Dedicated message (not "status") — any non-"listening" status
                    # stops Unity's mic, so this must not reuse that channel.
                    try:
                        await self._ws.send(json.dumps({"type": "hearing"}))
                    except Exception:
                        pass
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
        """Stream Claude reply sentence-by-sentence through the TTS pipeline."""
        if self._summarize_task is not None and not self._summarize_task.done():
            logger.info("[think_and_speak] Waiting for in-flight background summarization")
            await self._summarize_task
            self._summarize_task = None
        try:
            return await self._speak_turn(self._ai_client.stream_async(user_text), turn)
        except Exception as exc:
            logger.exception("[think_and_speak] Error: %s", exc)
            await self._send_error(str(exc))
            return "Sorry, I had a little trouble. Let me try again!"

    async def _speak_turn(self, chunk_aiter, turn) -> str:
        """Feed an async iterator of text chunks through the sentence splitter and TTS
        queue, then wait for Unity to finish playing every queued segment. Returns the
        full concatenated text once generation completes (not once playback completes)."""
        self._pending_speaks = 0
        self._all_done_event.set()  # will be cleared on first enqueued speak
        self._turn_drained_event.clear()
        self._speaking_started = False
        self._first_speak_sent_ts = None

        splitter = SentenceSplitter()
        reply_chunks: list[str] = []

        t_start = time.perf_counter()
        t_first_token: float | None = None
        t_first_sentence: float | None = None

        async for chunk in chunk_aiter:
            if t_first_token is None:
                t_first_token = time.perf_counter()
            reply_chunks.append(chunk)
            for sentence in splitter.feed(chunk):
                if t_first_sentence is None:
                    t_first_sentence = time.perf_counter()
                self._tts_q.put_nowait(sentence)

        if tail := splitter.flush():
            if t_first_sentence is None:
                t_first_sentence = time.perf_counter()
            self._tts_q.put_nowait(tail)

        self._tts_q.put_nowait(_TURN_END)
        full_reply = "".join(reply_chunks)

        # Wait for the worker to drain the queue, then for Unity to finish playback.
        await self._turn_drained_event.wait()
        if self._pending_speaks > 0:
            timeout = max(60.0, self._pending_speaks * 30.0)
            try:
                await asyncio.wait_for(self._all_done_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("[speak] Timed out waiting for Unity done(s)")

        t_end = time.perf_counter()
        logger.info(
            "[timing] turn=%s | first_token=+%.2fs first_sentence=+%.2fs "
            "first_speak=+%.2fs total=%.2fs",
            turn,
            (t_first_token - t_start) if t_first_token else -1,
            (t_first_sentence - t_start) if t_first_sentence else -1,
            (self._first_speak_sent_ts - t_start) if self._first_speak_sent_ts else -1,
            t_end - t_start,
        )
        return full_reply

    # ── TTS worker (single, session-lifetime task) ───────────────────────────

    async def _tts_worker(self) -> None:
        """Drains the TTS queue: synthesizes each sentence and forwards it to Unity.
        One worker preserves ordering with no sequence numbers; synthesis of sentence
        N overlaps LLM generation of N+1 (the producer never blocks on this)."""
        while True:
            item = await self._tts_q.get()
            if item is _WORKER_STOP:
                break
            if item is _TURN_END:
                self._turn_drained_event.set()
                continue
            try:
                await self._synthesize_and_send(item)
            except Exception as exc:
                logger.exception("[tts_worker] Unexpected error for %r: %s", item[:40], exc)

    async def _synthesize_and_send(self, text: str) -> None:
        """Synthesize one sentence (with one retry) and send it to Unity as a speak segment."""
        text = text.strip()
        if not text:
            return

        data = None
        for attempt in (1, 2):
            try:
                t0 = time.perf_counter()
                resp = await self._http.post(TTS_URL, json={"text": text})
                resp.raise_for_status()
                data = resp.json()
                logger.info("[speak] TTS %.2fs — %r", time.perf_counter() - t0, text[:60])
                break
            except Exception as exc:
                if attempt == 2:
                    logger.exception("[speak] TTS failed twice for %r: %s", text[:40], exc)
                    await self._send_error(f"tts_failed: {text[:60]}")
                    return
                logger.warning("[speak] TTS attempt failed for %r (%s) — retrying", text[:40], exc)
                await asyncio.sleep(0.5)

        self._pending_speaks += 1
        self._all_done_event.clear()
        if not self._speaking_started:
            self._speaking_started = True
            await self._status("speaking")
        if self._first_speak_sent_ts is None:
            self._first_speak_sent_ts = time.perf_counter()

        await self._ws.send(json.dumps({
            "type": "speak",
            "audio_base64": data["audio_base64"],
            "sample_rate": data["sample_rate"],
            "duration_ms": data["duration_ms"],
            "viseme_events": data.get("viseme_events", []),
            "text": text,
        }))

    # ── Greeting streaming (shares the same TTS pipeline) ─────────────────────

    async def _stream_claude_raw(self, system: str, messages: list, max_tokens: int, temperature: float):
        """Stream raw text from a one-off Claude call (not tied to session history)."""
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self._ai_client._api_key)
        async with client.messages.stream(
            model=self._ai_client.config.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            temperature=temperature,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def _new_greeting_stream(self, system_prompt: str):
        system = (
            system_prompt
            + "\n\nGenerate the opening greeting for a new session. "
            "Follow the 'Example Opening' in the instructions above. "
            "Keep it to 1-2 sentences max. "
            "IMPORTANT: Always end with a direct question or prompt that invites the child to respond "
            "(e.g. 'Can you say hello?' or 'Say: Hello!')."
        )
        messages = [{"role": "user", "content": "[New session — generate opening greeting]"}]
        async for chunk in self._stream_claude_raw(system, messages, max_tokens=100, temperature=0.8):
            yield chunk

    async def _welcome_back_stream(self, system_prompt: str):
        system = (
            system_prompt
            + "\n\nGenerate a brief, warm welcome-back greeting that naturally references "
            "one concrete detail from the prior conversation. 1-2 sentences max. "
            "Do not say 'welcome back' literally — make it feel natural. "
            "IMPORTANT: Always end with a question or prompt that invites the child to respond — "
            "for example: 'Can you still remember how to say it?' or 'Can you try saying it again?'"
        )
        history = self._ai_client._build_messages()
        messages = history + [{"role": "user", "content": "[Resume session — generate a welcome-back greeting]"}]
        async for chunk in self._stream_claude_raw(system, messages, max_tokens=128, temperature=0.8):
            yield chunk

    # ── Unity message handling ────────────────────────────────────────────────

    def on_unity_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        t = msg.get("type")
        if t == "done":
            self._pending_speaks = max(0, self._pending_speaks - 1)
            if self._pending_speaks == 0:
                self._all_done_event.set()
            logger.debug("[unity] done received — pending_speaks=%d", self._pending_speaks)
        elif t == "stop":
            self._stop_event.set()
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

    async def _send_transcript(self, text: str) -> None:
        try:
            await self._ws.send(json.dumps({"type": "transcript", "text": text}))
        except Exception:
            pass

    # ── Session persistence helpers ───────────────────────────────────────────

    async def _save_session_state(self) -> None:
        if self._session is None or self._ai_client is None:
            return
        from datetime import datetime, timezone
        usage = self._ai_client._last_usage
        if usage:
            self._session.last_input_tokens = usage.get("input_tokens", 0)
            self._session.last_output_tokens = usage.get("output_tokens", 0)
        self._session.messages = [
            {"role": m.role, "content": m.content}
            for m in self._ai_client._history
        ]
        self._session.updated_at = datetime.now(timezone.utc).isoformat()
        try:
            self._store.save(self._session)
        except Exception as exc:
            logger.warning("[session] Failed to save session: %s", exc)

    def _should_summarize(self) -> bool:
        if self._session is None:
            return False
        total = self._session.last_input_tokens + self._session.last_output_tokens
        return total > MAX_HISTORY_TOKENS

    async def _summarize_and_compact(self, system_prompt: str) -> None:
        if self._ai_client is None or self._session is None:
            return
        logger.info(
            "[session] Summarizing history (%d input + %d output tokens > %d limit)",
            self._session.last_input_tokens,
            self._session.last_output_tokens,
            MAX_HISTORY_TOKENS,
        )
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self._ai_client._api_key)
            history = self._ai_client._build_messages()
            response = await client.messages.create(
                model=self._ai_client.config.model,
                max_tokens=600,
                system=(
                    "Summarize the following conversation. Preserve: facts about the user, "
                    "ongoing topics, the user's level/preferences, lessons covered, names. "
                    "Aim for ~500 tokens. Output only the summary."
                ),
                messages=history,
                temperature=0.3,
            )
            summary = response.content[0].text.strip()
            logger.info("[session] Summary generated (%d chars)", len(summary))
            self._ai_client._history.clear()
            self._ai_client.summary_context = summary
            self._session.summary = summary
            self._session.messages = []
            self._session.last_input_tokens = 0
            self._session.last_output_tokens = 0
            await self._save_session_state()
        except Exception as exc:
            logger.warning("[session] Summarization failed: %s", exc)


# ── WebSocket server ──────────────────────────────────────────────────────────

async def _handle_client(websocket) -> None:
    addr = getattr(websocket, "remote_address", "unknown")
    logger.info("[orchestrator] Unity connected from %s", addr)
    session = ConversationSession(websocket)
    run_task = asyncio.create_task(session.run())

    try:
        async for raw in websocket:
            if isinstance(raw, bytes):
                session.on_audio_frame(raw)
                continue
            logger.debug("[orchestrator] Unity msg: %s", raw[:120])
            session.on_unity_message(raw)
    except websockets.exceptions.ConnectionClosed:
        logger.info("[orchestrator] Unity WebSocket closed")
    except Exception as exc:
        logger.exception("[orchestrator] Unexpected error in client handler: %s", exc)
    finally:
        session._stop_event.set()
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
