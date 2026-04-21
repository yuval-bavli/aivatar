from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


@dataclass
class ChatConfig:
    """Provider-agnostic configuration for an AI chat client."""
    model: str = ""                          # Provider-specific; each provider sets its own default if empty
    temperature: float = 0.7
    max_tokens: int = 1024
    top_p: float = 1.0
    stop_sequences: List[str] = field(default_factory=list)


@dataclass
class ChatMessage:
    """A single message in a conversation."""
    role: Literal["user", "assistant"]
    content: str


@dataclass
class ChatResponse:
    """Response from an AI chat completion."""
    content: str                             # The assistant's text reply
    model: str                               # Actual model used (may differ from config.model)
    usage: Optional[Dict[str, int]] = None  # {"input_tokens": N, "output_tokens": N}
    stop_reason: Optional[str] = None        # "end_turn", "max_tokens", "stop_sequence", etc.
