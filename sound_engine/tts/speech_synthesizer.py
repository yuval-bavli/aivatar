"""Main SpeechSynthesizer class — Azure-compatible async API."""
import asyncio
import os
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

from .._types import VisemeEvent, SentenceEvent, SpeechSynthesisResult
from .phonemizer.phonemizer import Phonemizer
from .viseme.viseme_scheduler import VisemeScheduler

if TYPE_CHECKING:
    from .aligner import WordAligner
    from .phoneme_aligner import PhonemeAligner


def _load_env():
    """Load .env from repo root if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        # Walk up from this file to find .env
        here = os.path.dirname(os.path.abspath(__file__))
        for _ in range(4):
            candidate = os.path.join(here, '.env')
            if os.path.exists(candidate):
                load_dotenv(candidate)
                return
            here = os.path.dirname(here)
    except ImportError:
        pass


_load_env()


class SpeechSynthesizer:
    """
    Azure-compatible TTS + viseme synthesizer.

    Provider priority:
    1. ElevenLabs if ELEVENLABS_API_KEY is set
    2. edge-tts (free, default)
    3. MockTTS (offline fallback)

    Usage:
        synth = SpeechSynthesizer()
        synth.viseme_received = lambda ev: print(ev)
        result = synth.speak_text("Hello world")
        # result.audio_data: WAV bytes
        # result.viseme_events: List[VisemeEvent]
    """

    def __init__(
        self,
        timing_mode: str = 'approximate',
        voice: Optional[str] = None,
        global_offset_ms: float = 0.0,
        time_scale: float = 1.0,
        tts_rate_pct: float = 0.0,
    ):
        self.timing_mode = timing_mode
        self.voice = voice
        self.global_offset_ms = global_offset_ms
        self.time_scale = time_scale
        self.tts_rate_pct = tts_rate_pct
        self.viseme_received: Optional[Callable[[VisemeEvent], None]] = None
        self._phonemizer = Phonemizer()
        self._scheduler = VisemeScheduler()
        self.phoneme_aligner: Optional['PhonemeAligner'] = None  # set by server — tries first
        self.word_aligner: Optional['WordAligner'] = None        # fallback if phoneme aligner fails

    async def speak_text_async(self, text: str) -> SpeechSynthesisResult:
        """Synthesize text asynchronously. Returns WAV + viseme events."""
        from .expression import strip as strip_tags
        plain_text = strip_tags(text)  # tags must never reach the phonemizer

        (provider_name, wav_bytes, duration_ms,
         sentence_boundaries, word_timings, word_list,
         phoneme_timings, word_phonemes) = \
            await self._synthesize_async(text)

        viseme_events = self._build_visemes(
            plain_text, sentence_boundaries, word_timings, word_list, duration_ms,
            phoneme_timings=phoneme_timings, word_phonemes=word_phonemes,
            wav_bytes=wav_bytes,
        )

        for ev in viseme_events:
            if self.viseme_received:
                self.viseme_received(ev)

        # Build sentence events from boundary data if available
        if sentence_boundaries:
            sentence_events = [
                SentenceEvent(text=sent_text, end_time_ms=start_ms + dur_ms)
                for sent_text, start_ms, dur_ms in sentence_boundaries
                if sent_text.strip()
            ]
        else:
            sentence_events = [SentenceEvent(text=text, end_time_ms=duration_ms)]

        return SpeechSynthesisResult(
            audio_data=wav_bytes,
            duration_ms=duration_ms,
            viseme_events=viseme_events,
            sentence_events=sentence_events,
        )

    def speak_text(self, text: str) -> SpeechSynthesisResult:
        """Synchronous wrapper around speak_text_async."""
        return asyncio.run(self.speak_text_async(text))

    async def _synthesize_async(self, text: str):
        """Try providers in order.

        Returns (name, wav_bytes, duration_ms, sentence_boundaries, word_timings, word_list).
        Exactly one of sentence_boundaries / word_timings will be populated;
        both may be None for ElevenLabs (equal-split fallback).
        """
        from .expression import strip as strip_tags
        plain_text = strip_tags(text)  # used for word lists and MockTTS

        # Check ElevenLabs
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if api_key:
            try:
                from .providers.elevenlabs_provider import ElevenLabsProvider
                provider = ElevenLabsProvider(api_key=api_key)
                wav_bytes, duration_ms, _ = provider.synthesize(text)
                return "elevenlabs", wav_bytes, duration_ms, None, None, None, None, None
            except Exception as e:
                print(f"[sound_engine] ElevenLabs failed ({e}), falling back to edge-tts")

        # Try edge-tts
        try:
            from .providers.edge_tts_provider import EdgeTTSProvider
            kwargs = {}
            if self.voice:
                kwargs['voice'] = self.voice
            if self.tts_rate_pct != 0.0:
                kwargs['base_rate_pct'] = self.tts_rate_pct
            provider = EdgeTTSProvider(**kwargs)
            wav_bytes, duration_ms, sentence_boundaries = \
                await provider.synthesize_async(text)
            # sentence_boundaries: [(sent_text, start_ms, dur_ms), ...]

            # ── Alignment: phoneme-level (MMS_FA) → word-level (whisper) → sentence ──
            word_list = [w for w in plain_text.split() if w]
            word_phonemes = self._phonemizer.phonemize_word_list(word_list)

            # 1. Phoneme-level forced alignment (GPU, ~100ms, best quality)
            if self.phoneme_aligner is not None and self.phoneme_aligner.available:
                try:
                    phoneme_timings = await asyncio.to_thread(
                        self.phoneme_aligner.align, wav_bytes, word_phonemes
                    )
                    if phoneme_timings is not None:
                        return ("edge-tts+phoneme", wav_bytes, duration_ms,
                                None, None, word_list, phoneme_timings, word_phonemes)
                except Exception as ae:
                    print(f"[sound_engine] phoneme alignment failed ({ae}), trying word aligner")

            # 2. Word-level alignment fallback (CPU whisper, ~400ms)
            if self.word_aligner is not None and self.word_aligner.available:
                try:
                    word_timings = await asyncio.to_thread(
                        self.word_aligner.align, wav_bytes, text
                    )
                    if word_timings is not None:
                        return ("edge-tts+align", wav_bytes, duration_ms,
                                None, word_timings, word_list, None, None)
                except Exception as ae:
                    print(f"[sound_engine] word alignment failed ({ae}), using sentence timing")

            return ("edge-tts", wav_bytes, duration_ms,
                    sentence_boundaries, None, None, None, None)
        except Exception as e:
            print(f"[sound_engine] edge-tts failed ({e}), falling back to MockTTS")

        # MockTTS fallback — provides per-word timings directly
        from .providers.mock_tts import MockTTS
        mock = MockTTS()
        wav_bytes, duration_ms, word_timings = mock.synthesize(plain_text)
        word_list = [w for w in plain_text.split() if w]
        return "mock", wav_bytes, duration_ms, None, word_timings, word_list, None, None

    def _build_visemes(
        self,
        text: str,
        sentence_boundaries: Optional[List[Tuple[str, float, float]]],
        word_timings: Optional[List[Tuple[float, float]]],
        word_list: Optional[List[str]],
        duration_ms: float,
        phoneme_timings: Optional[List[Tuple[float, float]]] = None,
        word_phonemes: Optional[List[Tuple[str, List[str]]]] = None,
        wav_bytes: Optional[bytes] = None,
    ) -> List[VisemeEvent]:
        """Phonemize per sentence/word and schedule viseme events."""
        # Best path: phoneme-level MMS_FA timings — exact per-phoneme placement
        if phoneme_timings is not None and word_phonemes is not None:
            events = self._scheduler.schedule_phoneme_timings(
                flat_phoneme_timings=phoneme_timings,
                word_phonemes=word_phonemes,
                total_duration_ms=duration_ms,
                global_offset_ms=self.global_offset_ms,
                time_scale=self.time_scale,
            )
            return self._inject_pause_silences(events, wav_bytes, duration_ms)

        if sentence_boundaries:
            # edge-tts SentenceBoundary durations include trailing silence
            # padding, so the scheduler stretches phonemes into the audible
            # pauses. Tighten each window to the actual audio speech region(s)
            # so phonemes don't get distributed across silence.
            adjusted_boundaries = self._clip_boundaries_to_audio(
                sentence_boundaries, wav_bytes, duration_ms
            )
            sentence_data = []
            for sent_text, start_ms, dur_ms in adjusted_boundaries:
                words = [w for w in sent_text.split() if w]
                if not words:
                    continue
                phonemized = self._phonemizer.phonemize_word_list(words)
                sentence_data.append((start_ms, dur_ms, phonemized))
            events = self._scheduler.schedule_sentences(
                sentence_data=sentence_data,
                total_duration_ms=duration_ms,
                timing_mode=self.timing_mode,
                global_offset_ms=self.global_offset_ms,
                time_scale=self.time_scale,
            )
            return self._inject_pause_silences(events, wav_bytes, duration_ms)

        # MockTTS / ElevenLabs path: word_timings or equal-split fallback
        if word_list and word_timings:
            word_phonemes = self._phonemizer.phonemize_word_list(word_list)
        else:
            word_phonemes = self._phonemizer.phonemize_words(text)

        events = self._scheduler.schedule(
            word_phonemes=word_phonemes,
            word_timings=word_timings,
            total_duration_ms=duration_ms,
            timing_mode=self.timing_mode,
            global_offset_ms=self.global_offset_ms,
            time_scale=self.time_scale,
        )
        return self._inject_pause_silences(events, wav_bytes, duration_ms)

    # ── audio-aware silence handling ──────────────────────────────────────

    def _clip_boundaries_to_audio(
        self,
        sentence_boundaries: List[Tuple[str, float, float]],
        wav_bytes: Optional[bytes],
        duration_ms: float,
    ) -> List[Tuple[str, float, float]]:
        """Tighten each edge-tts sentence boundary to the audio's speech regions.

        edge-tts boundary durations include the inter-sentence silence padding
        as part of the sentence — distributing phonemes across the full window
        spreads them into the audible pause. Clipping to the speech regions
        (detected via RMS in audio_analyzer, stdlib only) keeps phonemes in
        the speech windows and lets the natural inter-sentence gap remain
        silent for the lip-sync.
        """
        if not wav_bytes or not sentence_boundaries:
            return sentence_boundaries
        try:
            from ..audio_analyzer import analyze_wav
            profile = analyze_wav(wav_bytes)
        except Exception:
            return sentence_boundaries
        if not profile.speech_regions:
            return sentence_boundaries

        speech = sorted(profile.speech_regions, key=lambda r: r.start_ms)
        claimed = [False] * len(speech)
        result: List[Tuple[str, float, float]] = []
        for sent_text, start_ms, dur_ms in sentence_boundaries:
            end_ms = start_ms + dur_ms
            owned = []
            for k, r in enumerate(speech):
                if claimed[k]:
                    continue
                center = (r.start_ms + r.end_ms) / 2.0
                if start_ms <= center < end_ms:
                    owned.append(r)
                    claimed[k] = True
            if owned:
                new_start = owned[0].start_ms
                new_end = owned[-1].end_ms
                result.append((sent_text, new_start, new_end - new_start))
            else:
                result.append((sent_text, start_ms, dur_ms))
        return result

    def _inject_pause_silences(
        self,
        events: List[VisemeEvent],
        wav_bytes: Optional[bytes],
        duration_ms: float,
        min_pause_ms: float = 200.0,
        edge_guard_ms: float = 100.0,
    ) -> List[VisemeEvent]:
        """Insert v=0 events at the start of long audio silence regions.

        Backstop for any scheduling path: if the audio has a silence longer
        than ``min_pause_ms`` that the schedule did not already mark with a
        v=0 event, place one at its start so the Unity controller closes
        the mouth. Skips the leading and trailing silences (already handled
        by the scheduler bookends).
        """
        if not wav_bytes:
            return events
        try:
            from ..audio_analyzer import analyze_wav
            profile = analyze_wav(wav_bytes)
        except Exception:
            return events

        TICKS = 10_000
        new_events = list(events)
        for region in profile.silence_regions:
            if region.duration_ms < min_pause_ms:
                continue
            if region.start_ms < edge_guard_ms:
                continue
            if region.end_ms > duration_ms - edge_guard_ms:
                continue
            new_events.append(VisemeEvent(0, int(region.start_ms * TICKS)))

        new_events.sort(key=lambda e: e.audio_offset)
        deduped: List[VisemeEvent] = []
        for ev in new_events:
            if not deduped or deduped[-1].viseme_id != ev.viseme_id:
                deduped.append(ev)
        return deduped
