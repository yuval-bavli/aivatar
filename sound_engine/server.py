"""HTTP server that wraps sound_engine for Unity integration.

Start before playing in Unity:
    .venv/Scripts/python sound_engine/server.py

Default port: 5123 (override with SOUND_ENGINE_PORT env var).

Unity sends:  POST /speak  {"text": "Hello world"}
Server returns: {"audio_base64": "...", "sample_rate": 22050, "duration_ms": 1234.5,
                 "viseme_events": [{"time_ms": 0.0, "viseme_id": 0}, ...]}
"""
import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sound_engine.speech_synthesizer import SpeechSynthesizer
from sound_engine.param_config import load as load_params


def _get_sample_rate(wav_bytes: bytes) -> int:
    """Read sample rate from WAV header (bytes 24-27)."""
    try:
        import struct
        # Walk chunks to find "fmt "
        pos = 12
        while pos < len(wav_bytes) - 8:
            chunk_id = wav_bytes[pos:pos + 4].decode('ascii', errors='replace')
            chunk_size = struct.unpack_from('<I', wav_bytes, pos + 4)[0]
            if chunk_id == 'fmt ':
                return struct.unpack_from('<I', wav_bytes, pos + 8)[0]
            pos += 8 + chunk_size
    except Exception:
        pass
    return 22050  # fallback


class SpeechHandler(BaseHTTPRequestHandler):
    _synthesizer = None

    @classmethod
    def get_synthesizer(cls) -> SpeechSynthesizer:
        if cls._synthesizer is None:
            cls._synthesizer = SpeechSynthesizer(timing_mode='enhanced')
        return cls._synthesizer

    def do_POST(self):
        if self.path != '/speak':
            self.send_error(404, 'Only POST /speak is supported')
            return

        length = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(length))
            text = str(body.get('text', ''))
        except Exception as e:
            self.send_error(400, f'Bad JSON: {e}')
            return

        if not text.strip():
            self.send_error(400, 'text is empty')
            return

        try:
            synth = self.get_synthesizer()
            # Reload optimizer params on every request so changes take effect
            # without restarting the server.
            params = load_params()
            synth.global_offset_ms = params.global_offset_ms
            synth.time_scale = params.time_scale
            result = synth.speak_text(text)
        except Exception as e:
            self.send_error(500, f'Synthesis failed: {e}')
            return

        sample_rate = _get_sample_rate(result.audio_data)
        response = {
            'audio_base64': base64.b64encode(result.audio_data).decode('utf-8'),
            'sample_rate': sample_rate,
            'duration_ms': result.duration_ms,
            'viseme_events': [
                {
                    'time_ms': e.audio_offset / 10000.0,
                    'viseme_id': e.viseme_id,
                }
                for e in result.viseme_events
            ],
        }
        payload = json.dumps(response).encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print(f'[sound_engine] {fmt % args}', flush=True)


if __name__ == '__main__':
    port = int(os.environ.get('SOUND_ENGINE_PORT', '5123'))
    server = HTTPServer(('127.0.0.1', port), SpeechHandler)
    print(f'[sound_engine] Listening on http://127.0.0.1:{port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('[sound_engine] Shutting down.')
