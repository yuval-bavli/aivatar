"""Real-time Speech-to-Text WebSocket server.

Start with:
    python -m sound_engine.stt.server
  or:
    python sound_engine/stt/server.py

Endpoints:
    GET  /health              - liveness check
    WS   /ws/transcribe       - main STT endpoint
         ?language=en|he|mixed - transcription language (default: en)

See README.md for the full WebSocket API reference.
"""

import asyncio
import json
import logging
import os
import sys
import time

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from log_utils import setup_logger  # noqa: E402

from .session import STTSession
from .transcriber import WhisperTranscriber
from .vad import SileroVAD

# ---------------------------------------------------------------------------
# Logging - file + console via shared log_utils
# ---------------------------------------------------------------------------
logger = setup_logger("stt_server")

# ---------------------------------------------------------------------------
# Application state (populated at startup)
# ---------------------------------------------------------------------------
app = FastAPI(title="Aivatar STT Server")

_vad: SileroVAD | None = None
_transcriber: WhisperTranscriber | None = None
_gpu_lock: asyncio.Lock | None = None  # serialises GPU inference across sessions


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def _startup() -> None:
    global _vad, _transcriber, _gpu_lock

    logger.info("=== Aivatar STT Server startup ===")

    t0 = time.perf_counter()
    logger.info("Loading Silero VAD...")
    _vad = SileroVAD()
    logger.info("Silero VAD ready (%.1fs)", time.perf_counter() - t0)

    t0 = time.perf_counter()
    logger.info("Loading faster-whisper model...")
    _transcriber = WhisperTranscriber()
    logger.info("faster-whisper ready — model=%s device=%s (%.1fs)",
                _transcriber.model_size, _transcriber.device, time.perf_counter() - t0)

    _gpu_lock = asyncio.Lock()

    # Warm-up: run one silent inference so the first real call isn't slow
    logger.info("Warming up Whisper model...")
    t0 = time.perf_counter()
    import numpy as _np
    _transcriber.transcribe(_np.zeros(16000, dtype=_np.float32), "en")
    logger.info("Whisper warm-up done (%.1fs)", time.perf_counter() - t0)

    logger.info("STT server ready — ws://0.0.0.0:8765/ws/transcribe")


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "model": _transcriber.model_size if _transcriber else None,
        "device": _transcriber.device if _transcriber else None,
        "model_loaded": _transcriber is not None,
    })


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/transcribe")
async def ws_transcribe(websocket: WebSocket, language: str = "en") -> None:
    """Main STT WebSocket endpoint.

    Query params:
        language (str): "en", "he", or "mixed". Default "en".

    Binary frames: raw PCM int16 le, 16kHz mono.
    Text frames:   JSON control messages (see README).
    """
    await websocket.accept()
    client = websocket.client
    logger.info("Client connected — addr=%s language=%s", client, language)

    session = STTSession(vad=_vad, language=language)
    utterance_count = 0

    try:
        while True:
            message = await websocket.receive()

            # ---------------------------------------------------------------
            # Binary message: raw PCM audio
            # ---------------------------------------------------------------
            if "bytes" in message and message["bytes"] is not None:
                pcm_bytes: bytes = message["bytes"]
                events = session.process_audio(pcm_bytes)

                for event in events:
                    await websocket.send_text(json.dumps(event))

                    if event.get("type") == "vad_event":
                        vad_ev = event.get("event")
                        logger.debug("VAD: %s", vad_ev)

                    if event.get("event") == "speech_end":
                        utterance_count += 1
                        audio = session.get_utterance()
                        if audio is None:
                            logger.debug("Utterance #%d too short — skipping", utterance_count)
                            session.reset()
                            continue

                        logger.debug("Utterance #%d: %.0f samples — transcribing...",
                                     utterance_count, len(audio))
                        t0 = time.perf_counter()
                        try:
                            async with _gpu_lock:
                                result = await asyncio.to_thread(
                                    _transcriber.transcribe,
                                    audio,
                                    session.language,
                                )
                        except Exception as exc:
                            logger.exception("Transcription error on utterance #%d", utterance_count)
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": f"Transcription failed: {exc}",
                            }))
                            session.reset()
                            continue

                        elapsed = time.perf_counter() - t0
                        logger.info("Transcript #%d [%s] %.0fms inference: %r",
                                    utterance_count, result.language,
                                    result.inference_ms, result.text)
                        logger.debug("Transcript timing: audio_ms=%.0f inference_ms=%.0f wall_s=%.2f",
                                     result.duration_ms, result.inference_ms, elapsed)

                        await websocket.send_text(json.dumps({
                            "type": "transcript",
                            "text": result.text,
                            "language": result.language,
                            "duration_ms": round(result.duration_ms),
                            "inference_ms": round(result.inference_ms),
                        }))

                        # Each VAD speech_end is a hard utterance boundary —
                        # emit the whole transcript as one sentence immediately.
                        if result.text.strip():
                            logger.info("Sentence: %r", result.text)
                            await websocket.send_text(json.dumps({
                                "type": "sentence",
                                "text": result.text.strip(),
                            }))

                        session.reset()

            # ---------------------------------------------------------------
            # Text message: JSON control
            # ---------------------------------------------------------------
            elif "text" in message and message["text"] is not None:
                try:
                    msg = json.loads(message["text"])
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON in control message")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON in text message",
                    }))
                    continue

                logger.debug("Control message: %s", msg)
                responses = session.process_control(msg)
                for resp in responses:
                    await websocket.send_text(json.dumps(resp))

    except WebSocketDisconnect:
        logger.info("Client disconnected — addr=%s utterances=%d", client, utterance_count)
    except RuntimeError as exc:
        # Starlette raises RuntimeError when the client drops mid-receive.
        if "disconnect" in str(exc).lower():
            logger.info("Client disconnected (mid-receive) — addr=%s", client)
        else:
            logger.exception("Unexpected WebSocket RuntimeError: %s", exc)
    except Exception as exc:
        logger.exception("Unexpected WebSocket error: %s", exc)
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(exc),
            }))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.environ.get("STT_HOST", "0.0.0.0")
    port = int(os.environ.get("STT_PORT", "8765"))
    logger.info("=== STT server starting on ws://%s:%d ===", host, port)
    uvicorn.run("sound_engine.stt.server:app", host=host, port=port, reload=False)
