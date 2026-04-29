"""Persistent session storage for conversation history."""
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Session:
    session_id: str
    profile: str
    created_at: str
    updated_at: str
    messages: list = field(default_factory=list)
    summary: str | None = None
    last_input_tokens: int = 0
    last_output_tokens: int = 0


class SessionStore:
    def __init__(self, sessions_dir: Path):
        self._dir = sessions_dir

    def _profile_dir(self, profile: str) -> Path:
        d = self._dir / profile
        d.mkdir(parents=True, exist_ok=True)
        return d

    def latest_for_profile(self, profile: str) -> Session | None:
        pdir = self._profile_dir(profile)
        files = sorted(pdir.glob("*.json"), reverse=True)
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                return Session(**data)
            except Exception:
                continue
        return None

    def all_for_profile(self, profile: str) -> list[Session]:
        pdir = self._profile_dir(profile)
        sessions = []
        for f in sorted(pdir.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                sessions.append(Session(**data))
            except Exception:
                continue
        return sessions

    def new(self, profile: str) -> Session:
        now = datetime.now(timezone.utc).isoformat()
        session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return Session(
            session_id=session_id,
            profile=profile,
            created_at=now,
            updated_at=now,
        )

    def save(self, session: Session) -> None:
        pdir = self._profile_dir(session.profile)
        target = pdir / f"{session.session_id}.json"
        data = json.dumps(asdict(session), ensure_ascii=False, indent=2)
        fd, tmp = tempfile.mkstemp(dir=pdir, suffix=".json.tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(data)
            os.replace(tmp, target)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
