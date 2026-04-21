from dataclasses import dataclass, field
from typing import List


@dataclass
class VisemeEvent:
    viseme_id: int      # Azure viseme ID 0-14
    audio_offset: int   # 100-nanosecond ticks (1 ms = 10,000 ticks)


@dataclass
class SentenceEvent:
    text: str           # The sentence text
    end_time_ms: float  # When this sentence finishes (ms from audio start)


@dataclass
class SpeechSynthesisResult:
    audio_data: bytes           # WAV bytes
    duration_ms: float
    viseme_events: List[VisemeEvent] = field(default_factory=list)
    sentence_events: List[SentenceEvent] = field(default_factory=list)
