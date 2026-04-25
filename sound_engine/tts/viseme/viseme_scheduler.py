"""Word-anchored viseme timing scheduler."""
from typing import List, Optional, Tuple

from ..._types import VisemeEvent
from .arpabet_to_viseme import phoneme_to_viseme, PHONEME_WEIGHT

MS_TO_TICKS = 10_000  # 1 ms = 10,000 100-nanosecond ticks

# Type alias: [(sentence_start_ms, sentence_dur_ms, [(word, [phones]), ...]), ...]
SentenceData = List[Tuple[float, float, List[Tuple[str, List[str]]]]]


class VisemeScheduler:
    """
    Distributes phonemes across time windows to produce VisemeEvent lists.

    Two modes:
    - 'approximate': equal duration per phoneme within each word window
    - 'enhanced': phoneme-category-weighted durations (vowels longer, stops shorter)
    """

    def schedule(
        self,
        word_phonemes: List[Tuple[str, List[str]]],
        word_timings: Optional[List[Tuple[float, float]]],  # [(start_ms, duration_ms), ...]
        total_duration_ms: float,
        timing_mode: str = 'approximate',
        global_offset_ms: float = 0.0,
        time_scale: float = 1.0,
    ) -> List[VisemeEvent]:
        """
        Args:
            word_phonemes: [(word, [phones]), ...] in order
            word_timings: per-word (start_ms, duration_ms), or None to use equal split
            total_duration_ms: total audio duration in ms
            timing_mode: 'approximate' or 'enhanced'
        Returns:
            List[VisemeEvent] sorted by audio_offset, with silence bookends
        """
        if not word_phonemes:
            return [VisemeEvent(0, 0), VisemeEvent(0, int(total_duration_ms * MS_TO_TICKS))]

        # Build per-word time windows
        if word_timings and len(word_timings) == len(word_phonemes):
            windows = word_timings
        else:
            # Equal split across total duration
            n = len(word_phonemes)
            per_word = total_duration_ms / n
            windows = [(i * per_word, per_word) for i in range(n)]

        events: List[VisemeEvent] = [VisemeEvent(0, 0)]  # leading silence

        for (word, phones), (start_ms, dur_ms) in zip(word_phonemes, windows):
            if not phones:
                continue
            offsets = self._distribute(phones, start_ms, dur_ms, timing_mode)
            for phone, offset_ms in zip(phones, offsets):
                vid = phoneme_to_viseme(phone)
                # Skip tongue/glottal gestures that map to neutral (e.g. L, HH)
                # so they don't close the mouth mid-word.
                if vid == 0:
                    continue
                events.append(VisemeEvent(vid, int(offset_ms * MS_TO_TICKS)))

        # Trailing silence
        events.append(VisemeEvent(0, int(total_duration_ms * MS_TO_TICKS)))

        # Sort by offset
        events.sort(key=lambda e: e.audio_offset)

        # Apply global offset and time scale if needed
        if global_offset_ms != 0.0 or time_scale != 1.0:
            adjusted: List[VisemeEvent] = []
            for ev in events:
                ms = (ev.audio_offset / MS_TO_TICKS) * time_scale + global_offset_ms
                ms = max(0.0, ms)
                adjusted.append(VisemeEvent(ev.viseme_id, int(ms * MS_TO_TICKS)))
            events = adjusted
            events.sort(key=lambda e: e.audio_offset)

        # Deduplicate consecutive identical viseme IDs
        deduped: List[VisemeEvent] = []
        for ev in events:
            if not deduped or deduped[-1].viseme_id != ev.viseme_id:
                deduped.append(ev)

        return deduped

    def schedule_sentences(
        self,
        sentence_data: SentenceData,
        total_duration_ms: float,
        timing_mode: str = 'approximate',
        global_offset_ms: float = 0.0,
        time_scale: float = 1.0,
    ) -> List[VisemeEvent]:
        """
        Schedule visemes from sentence-level time windows.

        For each sentence, distributes its duration across words weighted by
        phoneme count (roughly proportional to syllable count), then distributes
        phonemes within each word via _distribute.

        A silence event is inserted at the end of each sentence window so the
        mouth returns to rest between sentences instead of holding the last
        phoneme until the next one starts.
        """
        if not sentence_data:
            return [VisemeEvent(0, 0),
                    VisemeEvent(0, int(total_duration_ms * MS_TO_TICKS))]

        events: List[VisemeEvent] = [VisemeEvent(0, 0)]  # leading silence

        for sent_start_ms, sent_dur_ms, words in sentence_data:
            if not words:
                continue

            # Weight each word's slice by phoneme count (min 1 so empty words
            # don't consume zero time).
            weights = [max(1, len(phones)) for _, phones in words]
            total_w = sum(weights)
            cursor = sent_start_ms

            for (word, phones), w in zip(words, weights):
                win_dur = (w / total_w) * sent_dur_ms
                if phones:
                    offsets = self._distribute(phones, cursor, win_dur, timing_mode)
                    for phone, offset_ms in zip(phones, offsets):
                        vid = phoneme_to_viseme(phone)
                        # Skip silent phonemes inside a word (HH, L→v0 etc.)
                        # so they don't break vowel continuity (e.g. "Hello"
                        # should open the mouth once, not twice).
                        if vid == 0:
                            continue
                        events.append(VisemeEvent(vid, int(offset_ms * MS_TO_TICKS)))
                cursor += win_dur

            # Silence at sentence end so the mouth returns to rest before the
            # next sentence (or before trailing WAV silence after the last one).
            sent_end_ms = sent_start_ms + sent_dur_ms
            events.append(VisemeEvent(0, int(sent_end_ms * MS_TO_TICKS)))

        # Trailing silence bookend at the full audio duration
        events.append(VisemeEvent(0, int(total_duration_ms * MS_TO_TICKS)))

        events.sort(key=lambda e: e.audio_offset)

        # Apply global offset and time scale if needed
        if global_offset_ms != 0.0 or time_scale != 1.0:
            adjusted: List[VisemeEvent] = []
            for ev in events:
                ms = (ev.audio_offset / MS_TO_TICKS) * time_scale + global_offset_ms
                ms = max(0.0, ms)
                adjusted.append(VisemeEvent(ev.viseme_id, int(ms * MS_TO_TICKS)))
            events = adjusted
            events.sort(key=lambda e: e.audio_offset)

        # Deduplicate consecutive identical viseme IDs
        deduped: List[VisemeEvent] = []
        for ev in events:
            if not deduped or deduped[-1].viseme_id != ev.viseme_id:
                deduped.append(ev)

        return deduped

    def schedule_phoneme_timings(
        self,
        flat_phoneme_timings: List[Tuple[float, float]],
        word_phonemes: List[Tuple[str, List[str]]],
        total_duration_ms: float,
        global_offset_ms: float = 0.0,
        time_scale: float = 1.0,
    ) -> List[VisemeEvent]:
        """
        Schedule visemes from per-phoneme (start_ms, end_ms) timings.

        `flat_phoneme_timings` is a flat list — one (start_ms, end_ms) per
        ARPABET phoneme across ALL words, in the same order as
        iterating word_phonemes[i][1] for each i.  Comes from PhonemeAligner.

        Each phoneme fires at its start_ms. Silent phonemes (vid==0) inside a
        word are skipped to avoid mid-word mouth closure.
        """
        events: List[VisemeEvent] = [VisemeEvent(0, 0)]  # leading silence

        timing_iter = iter(flat_phoneme_timings)
        for word, phones in word_phonemes:
            in_word_non_sil = False
            for phone in phones:
                try:
                    start_ms, _end_ms = next(timing_iter)
                except StopIteration:
                    break
                vid = phoneme_to_viseme(phone)
                if vid == 0:
                    continue  # skip silent phonemes inside words
                events.append(VisemeEvent(vid, int(start_ms * MS_TO_TICKS)))
                in_word_non_sil = True

        events.append(VisemeEvent(0, int(total_duration_ms * MS_TO_TICKS)))
        events.sort(key=lambda e: e.audio_offset)

        if global_offset_ms != 0.0 or time_scale != 1.0:
            adjusted = []
            for ev in events:
                ms = (ev.audio_offset / MS_TO_TICKS) * time_scale + global_offset_ms
                adjusted.append(VisemeEvent(ev.viseme_id, int(max(0.0, ms) * MS_TO_TICKS)))
            events = adjusted
            events.sort(key=lambda e: e.audio_offset)

        deduped: List[VisemeEvent] = []
        for ev in events:
            if not deduped or deduped[-1].viseme_id != ev.viseme_id:
                deduped.append(ev)
        return deduped

    def _distribute(
        self,
        phones: List[str],
        start_ms: float,
        dur_ms: float,
        mode: str,
    ) -> List[float]:
        """Return list of start offsets (ms) for each phoneme in this word."""
        if len(phones) == 1:
            return [start_ms]

        if mode == 'enhanced':
            weights = [PHONEME_WEIGHT.get(p.upper(), 1.0) for p in phones]
            total_w = sum(weights)
            offsets = []
            cursor = start_ms
            for w in weights:
                offsets.append(cursor)
                cursor += (w / total_w) * dur_ms
            return offsets
        else:
            # approximate: equal slices
            slice_ms = dur_ms / len(phones)
            return [start_ms + i * slice_ms for i in range(len(phones))]
