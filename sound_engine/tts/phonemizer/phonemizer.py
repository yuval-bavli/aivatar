"""Orchestrates CMU dict lookup + rule-based fallback for phonemization."""
import re
from typing import Dict, List

from .cmu_dict import lookup as cmu_lookup
from .rule_fallback import word_to_arpabet


class Phonemizer:
    """Convert text to per-word ARPABET phoneme lists."""

    def phonemize(self, text: str) -> Dict[str, List[str]]:
        """
        Returns an ordered dict of {word: [ARPABET phones]} for each word in text.
        Keys preserve order (Python 3.7+ dict). Duplicate words will have separate entries
        since we return a list of (word, phones) pairs internally — use phonemize_words.
        """
        words = self._tokenize(text)
        return {word: self._lookup(word) for word in words}

    def phonemize_words(self, text: str) -> List[tuple]:
        """Returns [(word, [phones]), ...] preserving word order including duplicates."""
        return [(word, self._lookup(word)) for word in self._tokenize(text)]

    def phonemize_word_list(self, words: List[str]) -> List[tuple]:
        """Phonemize a pre-tokenized list of words, one output entry per input word.
        Words that are pure punctuation get an empty phoneme list (timing entry preserved)."""
        result = []
        for w in words:
            cleaned = re.sub(r"[^a-zA-Z'-]", '', w)
            phones = self._lookup(cleaned) if cleaned else []
            result.append((cleaned or w, phones))
        return result

    def _tokenize(self, text: str) -> List[str]:
        # Split on whitespace, strip punctuation, keep non-empty
        tokens = re.split(r'\s+', text.strip())
        words = []
        for t in tokens:
            cleaned = re.sub(r"[^a-zA-Z'-]", '', t)
            if cleaned:
                words.append(cleaned)
        return words

    def _lookup(self, word: str) -> List[str]:
        result = cmu_lookup(word)
        if result:
            return result
        return word_to_arpabet(word)
