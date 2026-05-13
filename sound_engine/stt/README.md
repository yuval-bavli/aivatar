# Aivatar STT Server

A real-time WebSocket speech-to-text server built for conversational AI. The server receives raw PCM audio from a client (e.g. a browser microphone), uses Silero VAD to detect when the user finishes speaking, then transcribes the complete utterance using faster-whisper running on a CUDA GPU. Typical end-to-end latency from the end of speech to transcript delivery is 500–800ms.

This is a **complete-utterance** system — no streaming/partial transcription. The client sends audio continuously; the server handles all silence detection and turn-taking logic internally.

---

## Prerequisites

- Python 3.11+
- NVIDIA GPU with CUDA support (tested on RTX 4070 Ti, 12GB VRAM)
- CUDA Toolkit 12.x installed (`nvidia-smi` should work)
- ffmpeg on PATH (optional, only needed if you use the TTS side)

---

## Installation

```bash
# From the repo root, activate the venv once per session:
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows

# Install PyTorch with CUDA support FIRST (adjust cu121 to your CUDA version)
pip install torch --index-url https://download.pytorch.org/whl/cu121

# Install remaining dependencies
pip install -r sound_engine/stt/requirements.txt
```

The faster-whisper `large-v3-turbo` model (~1.5GB) downloads automatically on first startup from Hugging Face.

The Silero VAD model (~10MB) downloads automatically via `torch.hub` on first startup.

---

## Starting the Server

```bash
# From the repo root:
python -m sound_engine.stt.server

# Or directly:
python sound_engine/stt/server.py
```

The server starts on `ws://0.0.0.0:8765`. Check it's alive:

```bash
curl http://localhost:8765/health
# {"status":"ok","model":"large-v3-turbo","device":"cuda","model_loaded":true}
```

Environment variables:
- `STT_HOST` — bind address (default `0.0.0.0`)
- `STT_PORT` — port (default `8765`)
- `LOG_LEVEL` — logging verbosity: `DEBUG`, `INFO`, `WARNING` (default `INFO`)

---

## Running the Test Client

### WAV file client

Provide a WAV file at 16kHz mono 16-bit signed PCM:

```bash
python -m sound_engine.stt.test_client path/to/audio.wav
python -m sound_engine.stt.test_client path/to/audio.wav --language he
python -m sound_engine.stt.test_client path/to/audio.wav --language mixed
```

The client streams the file in 100ms chunks (simulating real-time mic input) and prints every VAD event and transcript as it arrives.

To convert any audio file to the right format using ffmpeg:
```bash
ffmpeg -i input.mp3 -ar 16000 -ac 1 -f s16le output.wav
```

### Live microphone input

The Unity client (`unity/aivatar/Assets/Scripts/ConversationClient.cs`) captures the microphone and streams 16 kHz PCM frames into the orchestrator, which forwards them to this STT server. There is no standalone Python mic client — run Unity to test the full live path.

Languages available in the mic client:
- `en` — English
- `he` — Hebrew
- `mixed` — Hebrew/English auto-detect (see below)

---

## WebSocket API Reference

**Endpoint:** `ws://localhost:8765/ws/transcribe?language=en`

| Query param | Values | Default | Description |
|-------------|--------|---------|-------------|
| `language` | `en`, `he`, `mixed` | `en` | Tran scription language. See language modes below. |

#### Language modes

| Value | Behaviour |
|-------|-----------|
| `en` | Force English. Fastest, most accurate for English-only speech. |
| `he` | Force Hebrew. Fastest, most accurate for Hebrew-only speech. |
| `mixed` | Detect language per utterance, restricted to English and Hebrew. Use when the speaker code-switches between the two. Runs a fast language-detection pass (~50ms) before transcription to pick the better language — output is never Spanish, French, or anything else. Adds ~50–100ms latency. |

### Client → Server

**Binary frames:** Raw PCM audio
- Format: 16kHz, mono, 16-bit signed little-endian (s16le)
- Any chunk size is accepted; 1024–3200 bytes (32–100ms) is typical

**Text frames:** JSON control messages

```json
// Update configuration at runtime
{"type": "config", "language": "mixed", "vad_silence_ms": 600}
// language can be "en", "he", or "mixed"

// Reset session state (clear buffers, return to LISTENING)
{"type": "reset"}
```

### Server → Client

**Transcript result** (sent after each detected utterance):
```json
{
  "type": "transcript",
  "text": "שלום, מה שלומך?",
  "language": "mixed",
  "duration_ms": 2340,
  "inference_ms": 210
}
```

The `language` field echoes back whatever was configured (`"en"`, `"he"`, or `"mixed"`). In mixed mode it always returns `"mixed"` — the per-utterance detected language is not exposed in the response.

**Sentence events** (sent after each transcript, once per complete sentence):
```json
{"type": "sentence", "text": "Hello there."}
{"type": "sentence", "text": "How are you doing today?"}
```

Sentence events are designed for AI agent consumption. They guarantee complete sentences — no cut-off fragments — by accumulating transcript text across VAD utterances and splitting on terminal punctuation (`.!?`). If a transcript ends mid-sentence (no terminal punctuation), the fragment is buffered and prepended to the next transcript before splitting again.

For each utterance, the order of messages sent is:
1. `transcript` — the raw Whisper output (always sent)
2. Zero or more `sentence` events — only for sentences that are provably complete

**VAD events** (sent immediately on state transitions):
```json
{"type": "vad_event", "event": "speech_start"}
{"type": "vad_event", "event": "speech_end"}
```

**Errors:**
```json
{"type": "error", "message": "Transcription failed: ..."}
```

---

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `language` | `"en"` | Transcription language (`"en"`, `"he"`, or `"mixed"`). Pass in URL param or `config` message. |
| `vad_silence_ms` | `500` | Silence duration (ms) before speech_end fires. Increase for slow speakers, decrease for faster response. |

VAD internals (edit `vad.py` / `audio_buffer.py` to change):

| Constant | Default | Description |
|----------|---------|-------------|
| `SPEECH_THRESHOLD` | `0.5` | Silero probability above which a frame is "speech" |
| `PRE_BUFFER_S` | `0.3s` | Audio captured before speech_start to avoid clipping words |
| `MAX_UTTERANCE_S` | `30s` | Force-end transcription after this long |
| `MIN_UTTERANCE_S` | `0.3s` | Minimum utterance length; shorter sounds are ignored |

---

## Architecture & Tech Stack

### Design philosophy

The system is built around a single insight: **accuracy beats speed for conversational AI**. Rather than streaming partial transcriptions (which are noisier and require correction logic on the client), it accumulates the complete utterance, transcribes it once, and delivers a clean result. End-to-end latency from end-of-speech to transcript is typically 500–800ms — imperceptible in a conversation.

### Component overview

```
Client (microphone)
    │  binary WebSocket frames — raw PCM s16le, 16kHz mono
    ▼
┌─────────────────────────────────────────────────────┐
│  server.py  (FastAPI + uvicorn)                     │
│                                                     │
│  One STTSession per WebSocket connection            │
│  asyncio.Lock serialises GPU access across sessions │
└──────────┬──────────────────────────────────────────┘
           │
    ┌──────▼──────────────────────────────┐
    │  session.py  — state machine        │
    │                                     │
    │  LISTENING ──► SPEAKING             │
    │  (on speech)   (on 500ms silence)   │
    │       │               │             │
    │       ▼               ▼             │
    │  audio_buffer.py   triggers         │
    │  pre-speech ring   transcription    │
    │  + utterance buf                    │
    └──────┬──────────────────────────────┘
           │
    ┌──────▼──────────────────────────────┐
    │  vad.py  — Silero VAD  (CPU)        │
    │  512-sample chunks, prob 0–1        │
    │  threshold 0.5, resets per turn     │
    └─────────────────────────────────────┘
           │ speech_end → get_utterance()
    ┌──────▼──────────────────────────────┐
    │  transcriber.py  — faster-whisper   │
    │  large-v3-turbo, CUDA, float16      │
    │  beam_size=1, vad_filter=False      │
    └──────┬──────────────────────────────┘
           │  raw transcript text
    ┌──────▼──────────────────────────────┐
    │  sentence_buffer.py                 │
    │  Splits on [.!?], buffers trailing  │
    │  fragments across utterances        │
    └──────┬──────────────────────────────┘
           │
    {"type": "transcript", ...}           ← always sent (raw Whisper output)
    {"type": "sentence", "text": "..."}  ← one per complete sentence
           │
    ◄──────┘  WebSocket JSON responses → Client
```

### Technology choices

| Component | Technology | Why |
|-----------|-----------|-----|
| **Web server** | FastAPI + uvicorn | Native async WebSocket support; minimal overhead; standard in Python ML stacks |
| **Speech recognition** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) `large-v3-turbo` | CTranslate2-optimised Whisper — 4–8× faster than OpenAI Whisper at the same accuracy. `large-v3-turbo` is a distilled variant with near-large-v3 quality at ~½ the inference time |
| **Inference precision** | float16 on CUDA | ~3GB VRAM usage, ~2× faster than float32, no meaningful accuracy loss for speech |
| **Voice activity detection** | [Silero VAD](https://github.com/snakers4/silero-vad) | Sub-millisecond CPU inference per 32ms chunk; extremely low false-positive rate; no GPU needed |
| **Audio format** | PCM s16le, 16kHz mono | Whisper's native format — no resampling or decoding overhead |
| **Concurrency** | `asyncio` + `asyncio.to_thread` | VAD runs in the async loop (it's fast enough); Whisper runs in a thread pool so the event loop never blocks. A single `asyncio.Lock` queues concurrent transcription requests without dropping connections |
| **Mic capture** (client) | sounddevice | Thin wrapper over PortAudio; cross-platform; streams directly into numpy arrays |

### Audio pipeline detail

1. **Client** captures mic audio at 16kHz mono 16-bit and sends raw PCM in ~64ms WebSocket binary frames continuously.
2. **VAD** (`vad.py`) processes the stream in 512-sample (32ms) windows. Each window produces a speech probability in [0, 1].
3. **State machine** (`session.py`) transitions:
   - `LISTENING → SPEAKING` when probability ≥ 0.5. Prepends a 300ms pre-speech ring buffer so the first phoneme is never clipped.
   - `SPEAKING → LISTENING` after 500ms of consecutive silence. Emits `speech_end`, which triggers transcription.
   - Force-ends at 30s if the speaker hasn't paused (prevents unbounded memory growth).
4. **Transcription** (`transcriber.py`) normalises the int16 buffer to float32 [-1, 1]. For `en`/`he`, calls `model.transcribe(audio, language=lang, ...)` directly. For `mixed`, first calls `model.detect_language(audio)` to pick whichever of `en`/`he` has a higher probability, then transcribes with that language — ensuring output is never misidentified as Spanish, French, etc.
5. **Result** is sent back as a JSON WebSocket text frame with the transcript, language, audio duration, and inference time.

### Latency budget

| Stage | Typical time |
|-------|-------------|
| VAD silence detection (500ms threshold) | 500ms |
| faster-whisper inference on RTX 4070 Ti | 150–300ms |
| Language detection (`mixed` mode only) | ~50ms |
| WebSocket round-trip (localhost) | <5ms |
| **Total after end-of-speech (en/he)** | **~650–800ms** |
| **Total after end-of-speech (mixed)** | **~700–850ms** |
