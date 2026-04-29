# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Unity MCP server

A Unity MCP server is available — use it to make scene changes, run menu items, read console output, and manage GameObjects directly without asking the user to do it manually. Key tools: `mcp__unity__execute_menu_item`, `mcp__unity__manage_gameobject`, `mcp__unity__manage_scene`, `mcp__unity__read_console`, `mcp__unity__manage_components`, `mcp__unity__find_gameobjects`, `mcp__unity__refresh_unity`.

After editing script files on disk, always call `mcp__unity__refresh_unity` to trigger a domain reload, then check `mcpforunity://editor/state` (`compilation.is_compiling`) before running menu items or other editor actions.

If the Unity MCP server is not responding or tools fail, prompt the user to ensure Unity is open with the MCP-for-Unity package active.

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

Each service writes logs to its own subdirectory under `debug/logs/`, named `{service}_{YYYYMMDD_HHMMSS}.log`:
- `debug/logs/aivatar_app/` — orchestrator (Claude, STT/TTS coordination)
- `debug/logs/tts_server/` — TTS server
- `debug/logs/stt_server/` — STT server
- `debug/logs/unity/` — Unity-side AivatarLogger output

Check these first when diagnosing runtime errors — tracebacks and exceptions are written at DEBUG level to the file even when not shown on the console.

## Server management workflow after code changes

After modifying any server file (`sound_engine/`, `aivatar_app/`, or `aivatar_ctl.py`):

1. Run `--status` to check the current state:
   ```bash
   .venv/Scripts/python aivatar_ctl.py --status
   ```
2. If the overall status is **Running** or **Partially-running**, immediately restart so the changes take effect:
   ```bash
   .venv/Scripts/python aivatar_ctl.py --restart
   ```
3. If the overall status is **Stopped**, no restart is needed — leave the servers stopped.

## Server management (aivatar_ctl)

`aivatar_ctl.py` manages all three servers from a single command.
Requires `psutil` — already installed in the venv.

```bash
.venv/Scripts/python aivatar_ctl.py --status   # show which servers are running
.venv/Scripts/python aivatar_ctl.py --start    # start any servers not already running
.venv/Scripts/python aivatar_ctl.py --restart  # stop all, then start fresh (picks up latest code)
.venv/Scripts/python aivatar_ctl.py --exit     # graceful stop (force-kills after 6 s)
```

Servers are started in dependency order (TTS → STT → orchestrator) and detected by TCP port.
Servers are background processes; their stdout/stderr go to the existing `debug/logs/` directories.

## Running the servers manually

```bash
# TTS — HTTP on port 5123
.venv/Scripts/python -m sound_engine.tts.server

# STT — WebSocket on port 8765
.venv/Scripts/python -m sound_engine.stt.server

# Health check STT
curl http://localhost:8765/health
```

## Running the full conversation loop (AI tutor avatar)

Use `aivatar_ctl.py --start` (above) or start three processes manually, then press Play in Unity:

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

This is an AI avatar system with real-time lip sync. The runtime target is Unity (`unity/aivatar/Assets/`, C# scripts driving an animation-clip-based viseme rig), fed by the Python `sound_engine` package.

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
- `ConversationClient.cs` — WebSocket client to the orchestrator; drives the full conversation loop
- `AnimClipLipSync.cs` — active lip sync controller; plays Azure visemes against the pre-baked animation clip
- `LipSyncBase.cs` — abstract base referenced by `ConversationClient.lipSyncController`
- `AudioVisemeDecoder.cs` — shared helper: base64 WAV → `AudioClip` + `VisemeTimeline`
- `VisemeTimeline.cs` / `VisemeEvent.cs` — viseme schedule data structures
- `VisemeMapping.cs` — ScriptableObject mapping Azure viseme ID → blendshape name
- `MicrophoneIndicatorUI.cs` / `StopButtonUI.cs` — uGUI overlay widgets
- `AivatarLogger.cs` — file-backed logger writing to `debug/logs/unity/`
- `AzureSpeechManager.cs` + `TestSpeak.cs` — legacy direct-TTS smoke-test path (kept for quick Azure-only validation; not on the production runtime path)
- Credentials from `.env` at repo root, loaded by `Editor/EnvLoader.cs`

Setup: menu `Aivatar > Setup Avatar Scene` wires the scene (Avatar + ConversationManager + Stop button + Microphone indicator).


### Live parameter tuning

Edit `lipsync_params.json` (at repo root) while the TTS server is running — it reloads on every `/speak` request:
```json
{"global_offset_ms": 0, "time_scale": 1.0, "weights": {...}}
```

## Hard constraints

- `audio_offset` in `VisemeEvent` is always in **100-nanosecond ticks** (`ms × 10000`) — Unity `AudioVisemeDecoder.cs` and the lip-sync controllers depend on this unit.
- Viseme IDs 0–14 in `tts/viseme/arpabet_to_viseme.py` must match the Azure IDs used in `VisemeMapping`.
- Provider fallback order must stay: ElevenLabs → edge-tts → MockTTS.
