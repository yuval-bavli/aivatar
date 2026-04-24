"""Smoke tests for SentenceSplitter."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aivatar_app.sentence_splitter import SentenceSplitter


def _feed_all(text: str, chunk_size: int = 5) -> list[str]:
    splitter = SentenceSplitter()
    results = []
    for i in range(0, len(text), chunk_size):
        results.extend(splitter.feed(text[i:i + chunk_size]))
    if tail := splitter.flush():
        results.append(tail)
    return results


def test_basic():
    out = _feed_all("Hello! How are you? I am fine.")
    assert out == ["Hello!", "How are you?", "I am fine."], out


def test_no_punctuation():
    out = _feed_all("hello there")
    assert out == ["hello there"], out


def test_single_word():
    out = _feed_all("yes")
    assert out == ["yes"], out


def test_multi_sentence():
    out = _feed_all("Okay. Got it!")
    assert out == ["Okay.", "Got it!"], out


def test_exclamation():
    out = _feed_all("Good job! Now try again.")
    assert out == ["Good job!", "Now try again."], out


def test_empty():
    splitter = SentenceSplitter()
    assert splitter.feed("") == []
    assert splitter.flush() is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"  PASS  {name}")
    print("All tests passed.")
