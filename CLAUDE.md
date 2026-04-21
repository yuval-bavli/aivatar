# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Python environment

Always use `.venv` at the repo root — never system Python or bare `pip`:
```bash
.venv/Scripts/python
.venv/Scripts/pip install -r sound_engine/requirements.txt
```

STT has a separate install step (needs CUDA torch):
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -r sound_engine/stt/requirements.txt
```

## Logs

All servers write structured logs to `debug/logs/` (one file per process, named `{service}_{YYYYMMDD_HHMMSS}.log`):
- `aivatar_app_*.log` — orchestrator (Claude, STT/TTS coordination)
- `tts_server_*.log` — TTS server
- `stt_server_*.log` — STT server
- `unity_*.log` — Unity-side AivatarLogger output

Check these first when diagnosing runtime errors — tracebacks and exceptions are written at DEBUG level to the file even when not shown on the console.

## Running the servers

```bash
# TTS — HTTP on port 5123
.venv/Scripts/python -m sound_engine.tts.server

# STT — WebSocket on port 8765
.venv/Scripts/python -m sound_engine.stt.server

# Health check STT
curl http://localhost:8765/health
```

## Running the full conversation loop (AI tutor avatar)

Start three processes (each in its own terminal), then press Play in Unity:

```bash
# Terminal 1 — TTS
.venv/Scripts/python -m sound_engine.tts.server

# Terminal 2 — STT  (needs CUDA GPU + separate torch install, see above)
.venv/Scripts/python -m sound_engine.stt.server

# Terminal 3 — Orchestrator (bridges STT → Claude → TTS → Unity)
.venv/Scripts/pip install -r aivatar_app/requirements.txt   # first time only
.venv/Scripts/python -m aivatar_app
```

In Unity: open `unity/aivatar`, run `Aivatar > Setup Avatar Scene` (once), then press Play.  
The avatar greets you; speak into your mic; conversation continues until you press Esc or the Stop button.

The orchestrator listens on `ws://127.0.0.1:5124` — Unity's `ConversationClient` connects to it automatically.

Profile: `profiles/english_tutor_heb/` (English tutor for Hebrew-speaking children).  
To change profile, set `AVATAR_PROFILE=<folder_name>` before launching the orchestrator.

## Testing

Quick offline smoke test (no network, no ffmpeg):
```bash
.venv/Scripts/python -c "
import sys; sys.path.insert(0,'.')
from sound_engine.tts.providers.mock_tts import MockTTS
from sound_engine.tts.phonemizer.phonemizer import Phonemizer
from sound_engine.tts.viseme.viseme_scheduler import VisemeScheduler
mock = MockTTS()
wav, dur, timings = mock.synthesize('hello world')
ph = Phonemizer()
events = VisemeScheduler().schedule(ph.phonemize_words('hello world'), None, dur)
print([(e.viseme_id, e.audio_offset//10000) for e in events])
"
```

Full TTS test (needs internet + ffmpeg):
```bash
.venv/Scripts/python sound_engine/tts/examples/usage.py approximate
.venv/Scripts/python sound_engine/tts/examples/usage.py enhanced
```

STT test with a WAV file:
```bash
.venv/Scripts/python -m sound_engine.stt.test_client path/to/audio.wav --language en
```

## Project architecture

This is an AI avatar system with real-time lip sync. Two parallel runtime targets:
- **Web**: `avatar.html` (Three.js, Azure Speech SDK in the browser)
- **Unity**: `unity/aivatar/Assets/` (C# scripts driving blendshapes)

Both are fed by the Python `sound_engine` package.

### sound_engine

The core Python audio backend — two independent subsystems:

**TTS (port 5123, HTTP POST `/speak`)**
`text` → provider (ElevenLabs → edge-tts → MockTTS) → phonemizer → viseme scheduler → `SpeechSynthesisResult`  
Returns: `audio_base64`, `sample_rate`, `duration_ms`, `viseme_events` (Azure IDs 0–14, offsets in 100ns ticks), `sentence_events`.

**STT (port 8765, WebSocket `/ws/transcribe`)**
Raw 16kHz mono 16-bit PCM → Silero VAD → faster-whisper (GPU) → transcript/sentence JSON messages.

TTS and STT are separate processes with no shared state. See `sound_engine/CLAUDE.md` for implementation details, timing quirks, and constraints.

### Unity integration

`unity/aivatar/Assets/Scripts/`:
- `AzureSpeechManager.cs` — calls TTS server directly (legacy / smoke-test path)
- `AudioVisemeDecoder.cs` — shared helper: base64 WAV → `AudioClip` + `VisemeTimeline`
- `ConversationClient.cs` — WebSocket client to the orchestrator; drives full conversation loop
- `StopButtonUI.cs` — wires a uGUI Button to `ConversationClient.Stop()`
- `ProLipSync.cs` — drives `SkinnedMeshRenderer` blendshapes from `VisemeTimeline`
- `VisemeMapping.cs` — ScriptableObject mapping Azure viseme ID → blendshape name
- Credentials from `.env` at repo root, loaded by `EnvLoader.cs` editor script

Setup: menu `Aivatar > Setup Avatar Scene` wires the scene (Avatar + ConversationManager + Stop button).


### Live parameter tuning

Edit `sound_engine/lipsync_params.json` while the TTS server is running — it reloads on every `/speak` request:
```json
{"global_offset_ms": 0, "time_scale": 1.0, "weights": {...}}
```

## Hard constraints

- `audio_offset` in `VisemeEvent` is always in **100-nanosecond ticks** (`ms × 10000`) — Unity `AzureSpeechManager.cs` depends on this unit.
- Viseme IDs 0–14 in `tts/viseme/arpabet_to_viseme.py` must match Azure IDs used in `VisemeMapping` and `avatar.html`.
- Provider fallback order must stay: ElevenLabs → edge-tts → MockTTS.
