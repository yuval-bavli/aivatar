"""Real-time Speech-to-Text WebSocket server.

Start with:
    .venv/Scripts/python -m sound_engine.stt.server
  or:
    .venv/Scripts/python sound_engine/stt/server.py

Endpoints:
    GET  /health              — liveness check
    WS   /ws/transcribe       — main STT endpoint
         ?language=en|he|mixed — transcription language (default: en)

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

from .session import STTSession
from .transcriber import WhisperTranscriber
from .vad import SileroVAD

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

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
    _vad = SileroVAD()
    logger.info("Silero VAD ready (%.1fs)", time.perf_counter() - t0)

    t0 = time.perf_counter()
    _transcriber = WhisperTranscriber()
    logger.info("faster-whisper ready (%.1fs)", time.perf_counter() - t0)

    _gpu_lock = asyncio.Lock()
    logger.info("Server ready — listening on ws://0.0.0.0:8765/ws/transcribe")


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
    logger.info("Client connected (language=%s)", language)

    session = STTSession(vad=_vad, language=language)

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

                    if event.get("event") == "speech_end":
                        # Run transcription off the event loop so the socket
                        # stays responsive to the next turn
                        audio = session.get_utterance()
                        if audio is None:
                            logger.debug("Utterance too short, skipping transcription")
                            session.reset()
                            continue

                        try:
                            async with _gpu_lock:
                                result = await asyncio.to_thread(
                                    _transcriber.transcribe,
                                    audio,
                                    session.language,
                                )
                        except Exception as exc:
                            logger.exception("Transcription error")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": f"Transcription failed: {exc}",
                            }))
                            session.reset()
                            continue

                        await websocket.send_text(json.dumps({
                            "type": "transcript",
                            "text": result.text,
                            "language": result.language,
                            "duration_ms": round(result.duration_ms),
                            "inference_ms": round(result.inference_ms),
                        }))
                        session.reset()

            # ---------------------------------------------------------------
            # Text message: JSON control
            # ---------------------------------------------------------------
            elif "text" in message and message["text"] is not None:
                try:
                    msg = json.loads(message["text"])
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON in text message",
                    }))
                    continue

                responses = session.process_control(msg)
                for resp in responses:
                    await websocket.send_text(json.dumps(resp))

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except RuntimeError as exc:
        # Starlette raises RuntimeError("Cannot call 'receive' once a disconnect
        # message has been received.") when the client drops mid-receive.
        # Treat this as a normal disconnect, not an error.
        if "disconnect" in str(exc).lower():
            logger.info("Client disconnected (mid-receive)")
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
    # Allow overriding host/port via env vars for Docker/dev convenience
    host = os.environ.get("STT_HOST", "0.0.0.0")
    port = int(os.environ.get("STT_PORT", "8765"))
    uvicorn.run("sound_engine.stt.server:app", host=host, port=port, reload=False)
