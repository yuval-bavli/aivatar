"""Letter-to-ARPABET rule-based fallback for out-of-vocabulary words."""
import re
from typing import List

# Ordered rules: check digraphs before single letters
_RULES = [
    # Digraphs first
    (r'ch',  ['CH']),
    (r'sh',  ['SH']),
    (r'th',  ['TH']),
    (r'ph',  ['F']),
    (r'wh',  ['W']),
    (r'ng',  ['NG']),
    (r'ck',  ['K']),
    (r'qu',  ['K', 'W']),
    (r'gh',  ['G']),
    (r'oo',  ['UW']),
    (r'ee',  ['IY']),
    (r'ea',  ['IY']),
    (r'ou',  ['AW']),
    (r'oi',  ['OY']),
    (r'ow',  ['OW']),
    (r'aw',  ['AO']),
    (r'ay',  ['EY']),
    (r'ai',  ['EY']),
    (r'au',  ['AO']),
    # Single letters
    (r'a',   ['AE']),
    (r'b',   ['B']),
    (r'c',   ['K']),
    (r'd',   ['D']),
    (r'e',   ['EH']),
    (r'f',   ['F']),
    (r'g',   ['G']),
    (r'h',   ['HH']),
    (r'i',   ['IH']),
    (r'j',   ['JH']),
    (r'k',   ['K']),
    (r'l',   ['L']),
    (r'm',   ['M']),
    (r'n',   ['N']),
    (r'o',   ['OW']),
    (r'p',   ['P']),
    (r'q',   ['K']),
    (r'r',   ['R']),
    (r's',   ['S']),
    (r't',   ['T']),
    (r'u',   ['AH']),
    (r'v',   ['V']),
    (r'w',   ['W']),
    (r'x',   ['K', 'S']),
    (r'y',   ['Y']),
    (r'z',   ['Z']),
]

# Pre-compile patterns anchored to start
_COMPILED = [(re.compile(r'^' + pat, re.IGNORECASE), phones) for pat, phones in _RULES]


def word_to_arpabet(word: str) -> List[str]:
    """Convert a word to an approximate ARPABET sequence using letter rules."""
    result: List[str] = []
    text = word.lower()
    while text:
        matched = False
        for pattern, phones in _COMPILED:
            m = pattern.match(text)
            if m:
                result.extend(phones)
                text = text[m.end():]
                matched = True
                break
        if not matched:
            # Skip non-alphabetic characters
            text = text[1:]
    return result if result else ['SIL']
