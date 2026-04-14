from dataclasses import dataclass, field
from typing import List


@dataclass
class VisemeEvent:
    viseme_id: int      # Azure viseme ID 0-14
    audio_offset: int   # 100-nanosecond ticks (1 ms = 10,000 ticks)


@dataclass
class SpeechSynthesisResult:
    audio_data: bytes           # WAV bytes
    duration_ms: float
    viseme_events: List[VisemeEvent] = field(default_factory=list)
