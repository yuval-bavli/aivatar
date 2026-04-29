# log_utils

Shared logging setup used by all aivatar servers (TTS, STT, orchestrator).

## Usage

Call once at process startup, before any other imports that use `logging`:

```python
from log_utils import setup_logger
logger = setup_logger("tts_server")
```

This configures the **root** logger with:
- A rotating file handler writing to `debug/logs/{name}/{name}_{YYYYMMDD_HHMMSS}.log`
- A console handler (INFO level)
- DEBUG level to file (full tracebacks visible in the file even when not shown on console)

All subsequent `logging.getLogger(__name__)` calls in the same process inherit the handlers automatically.

## Session transcripts

For per-client conversation logs (file only, no console output):

```python
from log_utils import setup_session_logger
session_log = setup_session_logger()
session_log.info("User: hello")
```

Files are written to `debug/logs/sessions/session_{NNN}_{YYYYMMDD_HHMMSS}.log`.

## Why a separate package?

Named `log_utils` (not `logging`) to avoid shadowing Python's stdlib `logging` module.
