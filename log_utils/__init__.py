"""
Shared logging setup for all aivatar servers.

Usage (call once at process startup before any other imports):
    from log_utils import setup_logger
    logger = setup_logger("tts_server")

Creates:
    debug/logs/{name}_{YYYYMMDD_HHMMSS}.log   — rotating file (10 MB / 5 backups)

Note: cannot name this package 'logging' — that would shadow Python's stdlib logging module.
"""
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_DEFAULT_LOG_DIR = _REPO_ROOT / "debug" / "logs"

_FMT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str,
    log_dir: Path | str | None = None,
    file_level: int = logging.DEBUG,
    console_level: int = logging.INFO,
) -> logging.Logger:
    """
    Configure the root logger with a rotating file handler and a console handler.

    Args:
        name:          Server name used in the log filename (e.g. "tts_server").
        log_dir:       Directory for log files. Defaults to <repo_root>/debug/logs/.
        file_level:    Minimum level written to the log file (default DEBUG).
        console_level: Minimum level written to stdout (default INFO).

    Returns:
        A named child logger (logging.getLogger(name)) after setting up handlers
        on the root logger. Call this once at startup; all subsequent
        logging.getLogger(__name__) calls in the same process inherit the handlers.
    """
    log_dir = Path(log_dir) if log_dir else _DEFAULT_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    start_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"{name}_{start_ts}.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers if called more than once in a process
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        fh = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB per file
            backupCount=5,
            encoding="utf-8",
        )
        fh.setLevel(file_level)
        fh.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))
        root.addHandler(fh)

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
               for h in root.handlers):
        ch = logging.StreamHandler()
        ch.setLevel(console_level)
        ch.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))
        root.addHandler(ch)

    named = logging.getLogger(name)
    named.info("Logging started → %s", log_path)
    return named
