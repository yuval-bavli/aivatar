"""Stream-safe sentence boundary splitter.

Buffers streaming text chunks and emits complete sentences as they arrive.
A sentence is complete when it ends with .  !  or  ? (optionally followed by
closing quotes/brackets).  The final fragment (no terminal punctuation) is
held in the buffer and returned via flush() at end-of-stream.

Usage:
    splitter = SentenceSplitter()
    for chunk in text_stream:
        for sentence in splitter.feed(chunk):
            process(sentence)
    if tail := splitter.flush():
        process(tail)
"""

import re

_BOUNDARY = re.compile(r'(?<=[.!?])\s+')
_TERMINAL = re.compile(r'[.!?][\"\'\)\]]*\s*$')


class SentenceSplitter:
    """Accumulates streaming text and yields complete sentences."""

    def __init__(self) -> None:
        self._buf = ""

    def feed(self, chunk: str) -> list[str]:
        """Add a text chunk. Returns list of complete sentences (may be empty)."""
        if not chunk:
            return []
        self._buf += chunk
        parts = _BOUNDARY.split(self._buf)
        complete: list[str] = []
        for i, part in enumerate(parts):
            stripped = part.strip()
            if not stripped:
                continue
            if _TERMINAL.search(stripped):
                complete.append(stripped)
            else:
                # Trailing fragment — reassemble remainder and hold it
                self._buf = " ".join(p for p in parts[i:] if p.strip())
                return complete
        self._buf = ""
        return complete

    def flush(self) -> str | None:
        """Return any buffered fragment. Clears the buffer."""
        out = self._buf.strip()
        self._buf = ""
        return out or None
