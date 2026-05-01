"""
Shared logging setup for all aivatar servers.

Usage (call once at process startup before any other imports):
    from log_utils import setup_logger
    logger = setup_logger("tts_server")

Creates:
    debug/logs/{name}/{name}_{YYYYMMDD_HHMMSS}.log   — rotating file (10 MB / 5 backups)

Note: cannot name this package 'logging' — that would shadow Python's stdlib logging module.
"""
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_DEFAULT_LOG_BASE = _REPO_ROOT / "debug" / "logs"

_FMT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str,
    log_dir: Path | str | None = None,
    file_level: int = logging.DEBUG,
    console_level: int = logging.INFO,
) -> logging.Logger:
    """
    Configure a named logger with its own rotating file handler.

    The console handler lives on the root logger (added once); the file handler
    is attached to the named logger so multiple services in the same process each
    write to their own log file without interfering with each other.

    Args:
        name:          Server name used in the log filename (e.g. "tts_server").
        log_dir:       Directory for log files. Defaults to <repo_root>/debug/logs/{name}/.
        file_level:    Minimum level written to the log file (default DEBUG).
        console_level: Minimum level written to stdout (default INFO).

    Returns:
        logging.getLogger(name) with a fresh RotatingFileHandler attached.
    """
    log_dir = Path(log_dir) if log_dir else _DEFAULT_LOG_BASE / name
    log_dir.mkdir(parents=True, exist_ok=True)

    start_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"{name}_{start_ts}.log"

    # Console handler — attached to root once so all loggers share it.
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    if not any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in root.handlers
    ):
        ch = logging.StreamHandler()
        ch.setLevel(console_level)
        ch.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))
        root.addHandler(ch)

    # File handler — attached to the named logger so each service gets its own file.
    named = logging.getLogger(name)
    named.setLevel(logging.DEBUG)
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in named.handlers):
        fh = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setLevel(file_level)
        fh.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))
        named.addHandler(fh)

    named.info("Logging started → %s", log_path)
    return named


_session_counter = 0


def setup_session_logger(log_dir: Path | str | None = None) -> logging.Logger:
    """
    Create a transcript logger for one client connection.

    Each call increments a global counter so files are always unique even if
    two sessions start within the same second.

    File: debug/logs/sessions/session_{NNN}_{YYYYMMDD_HHMMSS}.log
    Format: "2026-04-23 15:30:00 | Chatbot: Hi!"
    No console output — file only.  propagate=False so root handlers are bypassed.
    """
    global _session_counter
    _session_counter += 1
    session_num = _session_counter

    log_dir = Path(log_dir) if log_dir else _DEFAULT_LOG_BASE / "sessions"
    log_dir.mkdir(parents=True, exist_ok=True)

    start_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"session_{session_num:03d}_{start_ts}.log"

    session_log = logging.getLogger(f"session_{session_num}_{start_ts}")
    session_log.setLevel(logging.INFO)
    session_log.propagate = False  # don't forward to root (avoids polluting debug logs)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    session_log.addHandler(fh)

    return session_log
