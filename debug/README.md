# debug

Runtime logs and diagnostic data produced by all aivatar services.

## Log directories

| Directory | Service | Notes |
|-----------|---------|-------|
| `logs/aivatar_app/` | Orchestrator | Claude, STT/TTS coordination, WebSocket events |
| `logs/tts_server/` | TTS server | Synthesis requests, provider selection, viseme timing |
| `logs/stt_server/` | STT server | VAD decisions, Whisper transcriptions, sentence boundaries |
| `logs/unity/` | Unity client | C# `AivatarLogger` output forwarded from the editor |
| `logs/sessions/` | Per-session transcripts | Full conversation turn-by-turn (file only, no console) |

## Log file naming

```
{service}_{YYYYMMDD_HHMMSS}.log
```

Each process creates one file per startup. Rotating file handler: 10 MB per file, 5 backups.

## Log levels

- **Console:** INFO and above
- **File:** DEBUG and above (full tracebacks, timing details, token counts)

Check the file logs first when diagnosing runtime errors — exceptions are written at DEBUG level and may not appear on the console.

## images/

Debug screenshots and diagnostic images captured during development (e.g. lip sync alignment screenshots).

## Gitignore

Log files are git-ignored. The directory itself is tracked so the folder exists on a fresh clone.
