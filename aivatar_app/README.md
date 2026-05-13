# aivatar_app — Conversation Orchestrator

The brain that connects microphone → STT → Claude → TTS → Unity avatar.

## Architecture

```
mic (sounddevice)
    │
    ▼ 16 kHz s16le mono PCM
STT server ws://127.0.0.1:8765   (sound_engine.stt.server)
    │
    │ {"type":"sentence", "text":"..."}
    ▼
ClaudeChatClient  (ai_tools.claude.claude_client)
    │ profile: profiles/english_tutor_heb/
    │
    ▼ reply text
TTS server http://127.0.0.1:5123  (sound_engine.tts.server)
    │
    │ audio_base64 + viseme_events
    ▼
Unity WebSocket client (ConversationClient.cs)
    │ ws://127.0.0.1:5124
    └─ {"type":"speak", ...}  →  avatar lip-syncs and speaks
    └─ {"type":"done"}        ←  Unity signals playback finished
```

## Quickstart

**First time — install deps:**
```bash
pip install -r aivatar_app/requirements.txt  # Windows: .venv\Scripts\pip
```

**Env vars required (in `.env` at repo root):**
```
CLAUDE_KEY=sk-ant-...        # or ANTHROPIC_API_KEY
```

**Start in order (three terminals):**
```bash
# 1. TTS
python -m sound_engine.tts.server

# 2. STT  (needs CUDA GPU)
python -m sound_engine.stt.server

# 3. Orchestrator
python -m aivatar_app
# Windows: replace .venv/bin/ with .venv/Scripts/
```

Then press **Play** in the Unity editor. The avatar delivers the greeting and the conversation loop begins.

## Stopping

- Press **Esc** in Unity, or click the **Stop (Esc)** button.
- Or press **Ctrl+C** in the orchestrator terminal.

## Configuration

All via environment variables (set in `.env` or shell):

| Variable            | Default                              | Description                          |
|---------------------|--------------------------------------|--------------------------------------|
| `TTS_URL`           | `http://127.0.0.1:5123/speak`        | TTS server endpoint                  |
| `STT_URL`           | `ws://127.0.0.1:8765/ws/transcribe`  | STT server WebSocket                 |
| `ORCHESTRATOR_PORT` | `5124`                               | Port Unity connects to               |
| `AVATAR_PROFILE`    | `english_tutor_heb`                  | Profile folder under `profiles/`     |
| `CLAUDE_KEY`        | *(required)*                         | Anthropic API key                    |

## Wire protocol (orchestrator ↔ Unity)

**Server → Unity:**
```json
{"type": "speak",  "audio_base64": "...", "sample_rate": 22050, "duration_ms": 1234, "viseme_events": [...]}
{"type": "status", "state": "listening|thinking|speaking"}
{"type": "error",  "message": "..."}
```

**Unity → Server:**
```json
{"type": "done"}   // playback finished
{"type": "stop"}   // user pressed Esc or Stop button
```

## Profile format

Each profile is a folder under `profiles/`:
```
profiles/english_tutor_heb/
    system_prompt.md   — Claude system prompt (persona + teaching rules)
    greeting.txt       — First utterance (spoken before AI loop starts)
    lesson_*.md        — Lesson content referenced in the system prompt
```
