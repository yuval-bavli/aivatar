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
    _phoneme_aligner = None   # PhonemeAligner (MMS_FA, GPU) — primary path
    _word_aligner = None      # WordAligner (whisper, CPU) — fallback
    _aligners_loaded = False

    @classmethod
    def get_synthesizer(cls) -> SpeechSynthesizer:
        if cls._synthesizer is None:
            logger.info("Initialising SpeechSynthesizer (timing_mode=enhanced)…")
            t0 = time.perf_counter()
            cls._synthesizer = SpeechSynthesizer(timing_mode='enhanced')
            logger.info("SpeechSynthesizer ready (%.2fs)", time.perf_counter() - t0)
            # Attach aligners
            cls._load_aligners()
            cls._synthesizer.phoneme_aligner = cls._phoneme_aligner
            cls._synthesizer.word_aligner = cls._word_aligner
        return cls._synthesizer

    @classmethod
    def _load_aligners(cls):
        if cls._aligners_loaded:
            return
        cls._aligners_loaded = True

        # Phoneme aligner (MMS_FA, GPU) — on by default, set TTS_DISABLE_PHONEME_ALIGNER=1 to skip
        disabled = os.environ.get("TTS_DISABLE_PHONEME_ALIGNER", "").lower() in ("1", "true", "yes")
        if not disabled:
            try:
                from sound_engine.tts.phoneme_aligner import PhonemeAligner
                device = os.environ.get("TTS_ALIGNER_DEVICE", "cuda")
                cls._phoneme_aligner = PhonemeAligner(device=device)
                if cls._phoneme_aligner.available:
                    logger.info("PhonemeAligner ready (device=%s)", device)
                else:
                    logger.warning("PhonemeAligner loaded but not available")
                    cls._phoneme_aligner = None
            except Exception as exc:
                logger.warning("PhonemeAligner init failed (%s) — disabled", exc)
                cls._phoneme_aligner = None
        else:
            logger.info("PhonemeAligner disabled via TTS_DISABLE_PHONEME_ALIGNER")

        # Word aligner (whisper CPU) — only loaded if phoneme aligner is unavailable
        # or explicitly requested as backup
        if cls._phoneme_aligner is None:
            word_enabled = os.environ.get("TTS_ENABLE_WORD_ALIGNER", "false").lower() in ("1", "true", "yes")
            if word_enabled:
                try:
                    from sound_engine.tts.aligner import WordAligner
                    cls._word_aligner = WordAligner(device="cpu", model_size="base.en")
                except Exception as exc:
                    logger.warning("WordAligner init failed (%s)", exc)
                    cls._word_aligner = None

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
    # Warm up aligners and synthesizer at startup so the first request isn't slow
    SpeechHandler._load_aligners()
    SpeechHandler.get_synthesizer()
    host = os.environ.get('TTS_HOST', '127.0.0.1')
    server = HTTPServer((host, port), SpeechHandler)
    logger.info("TTS server ready — waiting for requests")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("TTS server shutting down.")
