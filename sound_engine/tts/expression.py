"""
Provider-agnostic expression markup for expressive TTS.

The LLM embeds style tags like [excited], [playful], [pause] inline in its replies.
This module parses them and provides per-provider rendering so the audio
actually sounds like a warm, engaged tutor instead of a text reader.

Supported tags
--------------
Styles:   [excited] [playful] [gentle] [curious] [silly] [whispered] [encouraging]
Pacing:   [pause]  [long pause]
Non-verbal: [laughs]  [sighs]  [gasps]

Provider rendering
------------------
edge-tts:       first style tag → global prosody kwargs (rate/pitch/volume);
                [pause]/[long pause] → <break> SSML embedded in text;
                non-verbal tags stripped.

ElevenLabs v3:  all tags pass through verbatim — eleven_v3 understands them natively;
                pacing tags become <break time="..."/> SSML.

Plain / phonemizer: all tags stripped, leaving clean prose.
"""

import re
from typing import Dict, Optional, Tuple

# Ordered so multi-word tags match before single-word prefixes (e.g. "long pause" before "pause")
_TAG_NAMES = (
    "excited|playful|gentle|curious|silly|whispered|encouraging"
    "|laughs|sighs|gasps"
    "|long pause|pause"
)
_TAG_RE = re.compile(rf"\[({_TAG_NAMES})\]", re.IGNORECASE)

KNOWN_STYLES: frozenset = frozenset([
    "excited", "playful", "gentle", "curious", "silly", "whispered", "encouraging",
])
KNOWN_NONVERBAL: frozenset = frozenset(["laughs", "sighs", "gasps"])
PACING: Dict[str, str] = {
    "pause": "350ms",
    "long pause": "700ms",
}

# Prosody values for edge-tts Communicate kwargs:
#   rate  → "+/-N%"  (relative to normal)
#   pitch → "+/-NHz" (relative to normal; edge-tts accepts Hz only)
#   volume→ "+/-N%"  (relative to normal)
STYLE_TO_PROSODY: Dict[str, Dict[str, str]] = {
    "excited":     {"rate": "+15%", "pitch": "+15Hz", "volume": "+20%"},
    "playful":     {"rate": "+10%", "pitch": "+10Hz"},
    "gentle":      {"rate": "-5%",  "pitch": "-5Hz"},
    "curious":     {"rate": "+5%",  "pitch": "+12Hz"},
    "silly":       {"rate": "+5%",  "pitch": "+20Hz"},
    "whispered":   {"rate": "-5%",  "pitch": "-8Hz",  "volume": "-40%"},
    "encouraging": {"pitch": "+5Hz", "volume": "+10%"},
}


def strip(text: str) -> str:
    """Remove all [tags] and return clean plain text for the phonemizer / visemes."""
    result = _TAG_RE.sub("", text)
    return re.sub(r" {2,}", " ", result).strip()


def primary_style(text: str) -> Optional[str]:
    """Return the first style tag name found in text, or None."""
    for m in _TAG_RE.finditer(text):
        tag = m.group(1).lower()
        if tag in KNOWN_STYLES:
            return tag
    return None


def to_edge_tts(text: str, base_rate_pct: float = 0.0) -> Tuple[str, Dict[str, str]]:
    """Prepare (rendered_text, prosody_kwargs) for edge-tts.

    - First style tag → prosody_kwargs dict (pass as **kwargs to Communicate)
    - base_rate_pct combined with style rate (e.g. -20 base + +15 excited = -5 total)
    - [pause] / [long pause] → stripped (edge-tts XML-escapes the text before SSML
      embedding, so injecting <break> tags causes them to be spoken literally)
    - Non-verbal and remaining style tags are stripped
    """
    style = primary_style(text)
    prosody: Dict[str, str] = dict(STYLE_TO_PROSODY[style]) if style else {}

    if base_rate_pct != 0.0:
        style_rate_str = prosody.get("rate", "")
        style_pct = int(style_rate_str.rstrip('%')) if style_rate_str else 0
        combined = int(base_rate_pct) + style_pct
        if combined != 0:
            prosody["rate"] = f"{combined:+d}%"
        elif "rate" in prosody:
            del prosody["rate"]

    rendered = _TAG_RE.sub("", text)
    rendered = re.sub(r" {2,}", " ", rendered).strip()
    return rendered, prosody


def to_elevenlabs_v3(text: str) -> str:
    """Prepare text for ElevenLabs eleven_v3.

    Style and non-verbal tags pass through verbatim (understood natively by v3).
    Pacing tags become <break time="..."/> SSML (also understood by v3).
    """
    def _replace(m: re.Match) -> str:
        tag = m.group(1).lower()
        if tag in PACING:
            return f'<break time="{PACING[tag]}"/>'
        return m.group(0)  # pass through as-is

    return _TAG_RE.sub(_replace, text)
