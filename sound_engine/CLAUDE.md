# sound_engine — Claude Notes

## Python environment
Always use `.venv` at the repo root:
- Install: `.venv/Scripts/pip install -r sound_engine/requirements.txt`
- Run: `.venv/Scripts/python sound_engine/tts/examples/usage.py`

## Key implementation facts

### Provider fallback chain
`SpeechSynthesizer._synthesize_async` tries providers in order and prints a warning on fallback:
1. ElevenLabs (if `ELEVENLABS_API_KEY` in env)
2. edge-tts (async, returns MP3 + WordBoundary events)
3. MockTTS (stdlib only, sine wave, no network)

### Word timing alignment
**edge-tts v7+ (current)** emits `SentenceBoundary` events only (per-sentence start+duration in 100ns ticks).  
**edge-tts v6** emitted `WordBoundary` events but v6 now gets 403 from the MS endpoint.

`EdgeTTSProvider` handles both: collects boundary events (Sentence or Word), then builds per-word timings by distributing words equally within each boundary window. This is far better than equal-split across total duration because leading/trailing silence and sentence gaps are preserved.

ElevenLabs and MockTTS pass `None` for `word_timings` → equal split fallback.

The phonemizer tokenizes the raw text independently of what the TTS provider returns. Word count may differ (e.g. punctuation stripping). `VisemeScheduler` handles mismatched lengths by falling back to equal split if `len(word_timings) != len(word_phonemes)`.

### Tick convention
`audio_offset` is in 100-nanosecond ticks: `offset_ticks = ms * 10_000`. This matches the Unity-side decoders (`AudioVisemeDecoder.cs`, `AnimClipLipSync.cs`). Do not change this unit.

### CMU dict
Lazy-loaded on first `Phonemizer` call. Downloads ~4 MB from NLTK on first use. Cached in `_cmu_dict` module-level dict for the process lifetime. Returns `None` (not raises) when nltk is missing or download fails — phonemizer then calls `rule_fallback.word_to_arpabet`.

### rule_fallback
Digraph rules must come before single-letter rules in `_RULES` list — order matters since patterns are matched left-to-right. Patterns are pre-compiled with `re.compile(r'^' + pat)`.

### WAV encoding
`wav_encoder.encode_raw_pcm_to_wav` wraps raw PCM bytes (already 16-bit LE). `encode_pcm_to_wav` takes a `List[int]` and packs with `struct`. `mp3_to_wav` uses pydub — will raise a clear error if ffmpeg is not on PATH.

### VisemeScheduler deduplication
Consecutive identical viseme IDs are collapsed into one event. This intentionally reduces jitter on repeated phonemes (e.g. "ll" in "hello" → single viseme 8 event).

## Testing
Quick smoke test (no network, no ffmpeg needed):
```bash
.venv/Scripts/python -c "
import sys; sys.path.insert(0,'.')
from sound_engine.tts.providers.mock_tts import MockTTS
from sound_engine.tts.phonemizer.phonemizer import Phonemizer
from sound_engine.tts.viseme.viseme_scheduler import VisemeScheduler
mock = MockTTS()
wav, dur, timings = mock.synthesize('hello world')
ph = Phonemizer()
events = VisemeScheduler().schedule(ph.phonemize_words('hello world'), None, dur)
print([(e.viseme_id, e.audio_offset//10000) for e in events])
"
```

Full test with real TTS (needs internet + ffmpeg):
```bash
.venv/Scripts/python sound_engine/tts/examples/usage.py approximate
.venv/Scripts/python sound_engine/tts/examples/usage.py enhanced
```

## TTS Server (`sound_engine/tts/`)

HTTP server on port 5123. See `tts/README.md` for full docs.

### Run
```bash
.venv/Scripts/python -m sound_engine.tts.server
```

### Key files
- `tts/server.py` — HTTP handler, `/speak` endpoint
- `tts/speech_synthesizer.py` — main orchestrator (providers → phonemizer → viseme)
- `tts/providers/` — ElevenLabs, edge-tts, MockTTS
- `tts/phonemizer/` — text → ARPABET
- `tts/viseme/` — ARPABET → Azure viseme IDs + timing scheduler

## What NOT to change
- `audio_offset` tick unit (must stay 100ns for Unity compatibility)
- Viseme ID table in `tts/viseme/arpabet_to_viseme.py` (must match Azure IDs 0–14 used in Unity's `VisemeMapping`)
- Provider fallback order (ElevenLabs → edge-tts → mock)

---

## STT Server (`sound_engine/stt/`)

Real-time speech-to-text WebSocket server. See `stt/README.md` for full docs.

### Install (separate from TTS — needs CUDA torch)
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -r sound_engine/stt/requirements.txt
```

### Run
```bash
.venv/Scripts/python -m sound_engine.stt.server
# Health check: curl http://localhost:8765/health
```

### Test with a WAV file
```bash
.venv/Scripts/python -m sound_engine.stt.test_client path/to/audio.wav --language en
```

### Key files
- `stt/server.py` — FastAPI app, WebSocket handler, asyncio.Lock for GPU
- `stt/session.py` — per-connection state machine (LISTENING / SPEAKING)
- `stt/vad.py` — Silero VAD wrapper (CPU, shared across sessions)
- `stt/audio_buffer.py` — pre-speech ring buffer + utterance accumulator
- `stt/transcriber.py` — faster-whisper large-v3-turbo wrapper (CUDA GPU)

### Architecture note
TTS (port 5123, HTTP) and STT (port 8765, WebSocket) are separate processes.
They do not share state. Run both if you need full duplex avatar conversation.
