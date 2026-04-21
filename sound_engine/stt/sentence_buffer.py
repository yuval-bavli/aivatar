"""Accumulates transcript fragments and emits complete sentences.

Whisper transcripts are split by VAD silence, not sentence boundaries.
This buffer holds a trailing fragment (no terminal punctuation) and
prepends it to the next transcript, so downstream consumers only
receive complete sentences.

Usage:
    buf = SentenceBuffer()
    for transcript_text in stream:
        sentences = buf.push(transcript_text)
        for s in sentences:
            send_to_agent(s)
    # At end of conversation, flush any remaining fragment:
    remaining = buf.flush()
"""

import re
from typing import List

# Sentence-ending punctuation followed by optional closing quotes/parens
_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')


class SentenceBuffer:
    """Splits streaming transcripts into complete sentences."""

    def __init__(self) -> None:
        self._pending: str = ""

    def push(self, text: str) -> List[str]:
        """Add a new transcript chunk. Returns list of complete sentences (may be empty)."""
        text = text.strip()
        if not text:
            return []

        combined = (self._pending + " " + text).strip() if self._pending else text

        parts = _SENTENCE_RE.split(combined)
        # parts: ["Hello there.", "How are you?", "I am"]
        #   ↑ complete sentences          ↑ trailing fragment (no terminal punct)

        complete: List[str] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if re.search(r'[.!?][\"\'\)\]]*$', part):
                complete.append(part)
            else:
                # Trailing fragment — hold it for next push
                self._pending = part
                return complete

        # Everything was complete
        self._pending = ""
        return complete

    def flush(self) -> str | None:
        """Return any buffered fragment (e.g. at end of conversation). Clears the buffer."""
        if self._pending:
            result = self._pending
            self._pending = ""
            return result
        return None

    def reset(self) -> None:
        """Discard any buffered fragment."""
        self._pending = ""
