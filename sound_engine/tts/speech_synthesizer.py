"""Main SpeechSynthesizer class — Azure-compatible async API."""
import asyncio
import os
from typing import Callable, List, Optional, Tuple

from .._types import VisemeEvent, SentenceEvent, SpeechSynthesisResult
from .phonemizer.phonemizer import Phonemizer
from .viseme.viseme_scheduler import VisemeScheduler


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
    ):
        self.timing_mode = timing_mode
        self.voice = voice
        self.global_offset_ms = global_offset_ms
        self.time_scale = time_scale
        self.viseme_received: Optional[Callable[[VisemeEvent], None]] = None
        self._phonemizer = Phonemizer()
        self._scheduler = VisemeScheduler()

    async def speak_text_async(self, text: str) -> SpeechSynthesisResult:
        """Synthesize text asynchronously. Returns WAV + viseme events."""
        (provider_name, wav_bytes, duration_ms,
         sentence_boundaries, word_timings, word_list) = \
            await self._synthesize_async(text)

        viseme_events = self._build_visemes(
            text, sentence_boundaries, word_timings, word_list, duration_ms,
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
        # Check ElevenLabs
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if api_key:
            try:
                from .providers.elevenlabs_provider import ElevenLabsProvider
                provider = ElevenLabsProvider(api_key=api_key)
                wav_bytes, duration_ms, _ = provider.synthesize(text)
                return "elevenlabs", wav_bytes, duration_ms, None, None, None
            except Exception as e:
                print(f"[sound_engine] ElevenLabs failed ({e}), falling back to edge-tts")

        # Try edge-tts
        try:
            from .providers.edge_tts_provider import EdgeTTSProvider
            kwargs = {}
            if self.voice:
                kwargs['voice'] = self.voice
            provider = EdgeTTSProvider(**kwargs)
            wav_bytes, duration_ms, sentence_boundaries = \
                await provider.synthesize_async(text)
            # sentence_boundaries: [(sent_text, start_ms, dur_ms), ...]
            return ("edge-tts", wav_bytes, duration_ms,
                    sentence_boundaries, None, None)
        except Exception as e:
            print(f"[sound_engine] edge-tts failed ({e}), falling back to MockTTS")

        # MockTTS fallback — provides per-word timings directly
        from .providers.mock_tts import MockTTS
        mock = MockTTS()
        wav_bytes, duration_ms, word_timings = mock.synthesize(text)
        word_list = [w for w in text.split() if w]
        return "mock", wav_bytes, duration_ms, None, word_timings, word_list

    def _build_visemes(
        self,
        text: str,
        sentence_boundaries: Optional[List[Tuple[str, float, float]]],
        word_timings: Optional[List[Tuple[float, float]]],
        word_list: Optional[List[str]],
        duration_ms: float,
    ) -> List[VisemeEvent]:
        """Phonemize per sentence/word and schedule viseme events."""
        if sentence_boundaries:
            # edge-tts path: phonemize each sentence's words, pass the whole
            # (start_ms, dur_ms, [(word, phones), ...]) structure to the
            # scheduler so it can weight by phoneme count.
            sentence_data = []
            for sent_text, start_ms, dur_ms in sentence_boundaries:
                words = [w for w in sent_text.split() if w]
                if not words:
                    continue
                phonemized = self._phonemizer.phonemize_word_list(words)
                sentence_data.append((start_ms, dur_ms, phonemized))
            return self._scheduler.schedule_sentences(
                sentence_data=sentence_data,
                total_duration_ms=duration_ms,
                timing_mode=self.timing_mode,
                global_offset_ms=self.global_offset_ms,
                time_scale=self.time_scale,
            )

        # MockTTS / ElevenLabs path: word_timings or equal-split fallback
        if word_list and word_timings:
            word_phonemes = self._phonemizer.phonemize_word_list(word_list)
        else:
            word_phonemes = self._phonemizer.phonemize_words(text)

        return self._scheduler.schedule(
            word_phonemes=word_phonemes,
            word_timings=word_timings,
            total_duration_ms=duration_ms,
            timing_mode=self.timing_mode,
            global_offset_ms=self.global_offset_ms,
            time_scale=self.time_scale,
        )
