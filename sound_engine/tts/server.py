"""HTTP server that wraps sound_engine/tts for Unity integration.

Start before playing in Unity:
    .venv/Scripts/python -m sound_engine.tts.server

Default port: 5123 (override with SOUND_ENGINE_PORT env var).

Unity sends:  POST /speak  {"text": "Hello world"}
Server returns: {"audio_base64": "...", "sample_rate": 22050, "duration_ms": 1234.5,
                 "viseme_events": [{"time_ms": 0.0, "viseme_id": 0}, ...]}
"""
import base64
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

# File + console logging must be set up before other imports that use logging
from log_utils import setup_logger  # noqa: E402
logger = setup_logger("tts_server")

from sound_engine.tts.speech_synthesizer import SpeechSynthesizer  # noqa: E402
from sound_engine.param_config import load as load_params           # noqa: E402


def _get_sample_rate(wav_bytes: bytes) -> int:
    try:
        import struct
        pos = 12
        while pos < len(wav_bytes) - 8:
            chunk_id = wav_bytes[pos:pos + 4].decode('ascii', errors='replace')
            chunk_size = struct.unpack_from('<I', wav_bytes, pos + 4)[0]
            if chunk_id == 'fmt ':
                return struct.unpack_from('<I', wav_bytes, pos + 8)[0]
            pos += 8 + chunk_size
    except Exception:
        pass
    return 22050


class SpeechHandler(BaseHTTPRequestHandler):
    _synthesizer: SpeechSynthesizer | None = None
    _aligner = None  # WordAligner, lazy-loaded

    @classmethod
    def get_synthesizer(cls) -> SpeechSynthesizer:
        if cls._synthesizer is None:
            logger.info("Initialising SpeechSynthesizer (timing_mode=enhanced)…")
            t0 = time.perf_counter()
            cls._synthesizer = SpeechSynthesizer(timing_mode='enhanced')
            logger.info("SpeechSynthesizer ready (%.2fs)", time.perf_counter() - t0)
            # Attach the word aligner (load it if not yet done)
            cls._synthesizer.word_aligner = cls.get_aligner()
        return cls._synthesizer

    @classmethod
    def get_aligner(cls):
        if cls._aligner is None:
            enabled = os.environ.get("TTS_ENABLE_WORD_ALIGNER", "false").lower() in ("1", "true", "yes")
            if not enabled:
                logger.info("WordAligner disabled (TTS_ENABLE_WORD_ALIGNER != true)")
                return None
            try:
                from sound_engine.tts.aligner import WordAligner
                cls._aligner = WordAligner(device="cpu", model_size="base.en")
            except Exception as e:
                logger.warning("WordAligner init failed (%s) — running without word alignment", e)
                cls._aligner = None
        return cls._aligner

    def do_POST(self):
        if self.path != '/speak':
            logger.warning("Unknown path: %s", self.path)
            self.send_error(404, 'Only POST /speak is supported')
            return

        length = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(length))
            text = str(body.get('text', ''))
        except Exception as e:
            logger.error("Bad JSON body: %s", e)
            self.send_error(400, f'Bad JSON: {e}')
            return

        if not text.strip():
            logger.warning("Received empty text in /speak request")
            self.send_error(400, 'text is empty')
            return

        preview = text[:80] + ("…" if len(text) > 80 else "")
        logger.info("→ /speak | text=%r", preview)

        try:
            synth = self.get_synthesizer()
            params = load_params()
            synth.global_offset_ms = params.global_offset_ms
            synth.time_scale = params.time_scale
            logger.debug("Params: global_offset_ms=%s time_scale=%s",
                         params.global_offset_ms, params.time_scale)

            t0 = time.perf_counter()
            result = synth.speak_text(text)
            elapsed = time.perf_counter() - t0

        except Exception as e:
            logger.exception("Synthesis failed for text %r: %s", preview, e)
            self.send_error(500, f'Synthesis failed: {e}')
            return

        sample_rate = _get_sample_rate(result.audio_data)
        audio_kb = len(result.audio_data) / 1024
        logger.info("← /speak | duration_ms=%.0f visemes=%d audio=%.1fkB elapsed=%.2fs",
                    result.duration_ms, len(result.viseme_events), audio_kb, elapsed)
        logger.debug("Provider used: %s", getattr(result, 'provider', 'unknown'))

        response = {
            'audio_base64': base64.b64encode(result.audio_data).decode('utf-8'),
            'sample_rate': sample_rate,
            'duration_ms': result.duration_ms,
            'viseme_events': [
                {'time_ms': e.audio_offset / 10000.0, 'viseme_id': e.viseme_id}
                for e in result.viseme_events
            ],
            'sentence_events': [
                {'text': se.text, 'end_time_ms': se.end_time_ms}
                for se in result.sentence_events
            ],
        }
        payload = json.dumps(response).encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        # Route BaseHTTPRequestHandler access logs through our logger
        logger.debug("[http] " + fmt, *args)


if __name__ == '__main__':
    port = int(os.environ.get('SOUND_ENGINE_PORT', '5123'))
    logger.info("=== TTS server starting on http://127.0.0.1:%d ===", port)
    # Warm up both aligner and synthesizer at startup so the first request isn't slow
    SpeechHandler.get_aligner()
    SpeechHandler.get_synthesizer()
    server = HTTPServer(('127.0.0.1', port), SpeechHandler)
    logger.info("TTS server ready — waiting for requests")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("TTS server shutting down.")
