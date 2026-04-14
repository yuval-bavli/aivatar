"""CMU Pronouncing Dictionary wrapper via nltk.corpus.cmudict."""
import re
from typing import Dict, List, Optional

_cmu_dict: Optional[Dict[str, List[str]]] = None


def _load() -> Optional[Dict[str, List[str]]]:
    global _cmu_dict
    if _cmu_dict is not None:
        return _cmu_dict
    try:
        import nltk
    except ImportError:
        return None  # Fall back to rule-based phonemizer

    try:
        entries = nltk.corpus.cmudict.entries()
    except LookupError:
        print("[sound_engine] Downloading CMU Pronouncing Dictionary (one-time)...")
        try:
            nltk.download('cmudict', quiet=True)
            entries = nltk.corpus.cmudict.entries()
        except Exception:
            return None  # Fall back to rule-based phonemizer

    # Build dict: word -> first pronunciation, stress markers stripped
    d: Dict[str, List[str]] = {}
    for word, phones in entries:
        if word not in d:
            d[word] = [re.sub(r'\d', '', p) for p in phones]
    _cmu_dict = d
    return _cmu_dict


def lookup(word: str) -> Optional[List[str]]:
    """Return ARPABET phoneme list for word, or None if not found. Stress digits stripped."""
    d = _load()
    if d is None:
        return None
    return d.get(word.lower())
