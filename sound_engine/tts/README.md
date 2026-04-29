# Aivatar TTS Server

A text-to-speech server that synthesizes speech, schedules viseme (mouth-shape) events for lip sync, and serves both as audio and timing data to Unity. The server wraps one of three TTS providers and produces a single unified response containing a WAV audio clip, per-viseme timestamps, and sentence boundary events.

---

## Prerequisites

- Python 3.11+
- ffmpeg on PATH (required for edge-tts and ElevenLabs MP3→WAV conversion)
  ```bash
  winget install ffmpeg          # Windows
  brew install ffmpeg            # macOS
  sudo apt install ffmpeg        # Linux
  ```
- Internet connection (for edge-tts or ElevenLabs; MockTTS works offline)

---

## Installation

```bash
# From repo root, activate your venv
.venv/Scripts/activate   # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r sound_engine/requirements.txt
```

---

## Starting the Server

```bash
# From repo root:
.venv/Scripts/python -m sound_engine.tts.server
```

The server starts on `http://127.0.0.1:5123`. Check it's alive:

```bash
curl http://127.0.0.1:5123/speak -X POST \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Hello.\"}"
```

Environment variables:
- `SOUND_ENGINE_PORT` — port (default `5123`)
- `ELEVENLABS_API_KEY` — use ElevenLabs instead of edge-tts

---

## HTTP API Reference

**Endpoint:** `POST /speak`

**Request:**
```json
{"text": "Hello there. How are you?"}
```

**Response:**
```json
{
  "audio_base64": "<base64-encoded WAV>",
  "sample_rate": 22050,
  "duration_ms": 1800.0,
  "viseme_events": [
    {"time_ms": 0.0,    "viseme_id": 0},
    {"time_ms": 42.5,   "viseme_id": 10},
    {"time_ms": 617.3,  "viseme_id": 0}
  ],
  "sentence_events": [
    {"text": "Hello there.", "end_time_ms": 800.0},
    {"text": "How are you?", "end_time_ms": 1800.0}
  ]
}
```

| Field | Description |
|-------|-------------|
| `audio_base64` | Base64-encoded WAV (16-bit PCM, mono) |
| `sample_rate` | Sample rate read from the WAV header |
| `duration_ms` | Total audio duration in milliseconds |
| `viseme_events` | Mouth-shape keyframes for lip sync (sorted by `time_ms`) |
| `sentence_events` | One entry per sentence with the sentence text and the time it finishes |

### Viseme IDs

Azure-compatible IDs 0–14:

| ID | Mouth shape | Example phonemes |
|----|-------------|-----------------|
| 0  | silence / rest | (pause) |
| 1  | PP | p, b, m |
| 2  | FF | f, v |
| 3  | TH | th |
| 4  | DD | d, t, n |
| 5  | kk | k, g |
| 6  | CH | ch, sh, zh |
| 7  | SS | s, z |
| 8  | nn | l, r |
| 9  | RR | r (rhotic) |
| 10 | aa | father, hot |
| 11 | E  | bed, said |
| 12 | ih | bit, gym |
| 13 | oh | go, boat |
| 14 | ou | boot, you |

### Sentence events

`sentence_events` contains one entry per complete sentence. Each entry has:
- `text` — the sentence text as synthesized
- `end_time_ms` — the time (ms from audio start) when this sentence finishes speaking

These are useful for feeding complete sentences to an AI agent without mid-sentence cuts.

---

## Provider Fallback Chain

The server tries providers in priority order and prints a warning when falling back:

```
1. ElevenLabs   (if ELEVENLABS_API_KEY is set in .env or environment)
2. edge-tts     (free, default — Microsoft Edge neural voices)
3. MockTTS      (offline fallback — 220 Hz sine wave, stdlib only)
```

### ElevenLabs
- Requires `ELEVENLABS_API_KEY` in `.env` at the repo root
- Returns MP3 → converted to WAV via pydub/ffmpeg
- No sentence boundary timing → equal-split fallback for viseme scheduling
- Voice: Rachel (`21m00Tcm4TlvDq8ikWAM`) by default

### edge-tts
- Free, no API key needed
- Uses Microsoft Edge neural voices over the network
- Default voice: `en-US-AriaNeural`
- Returns `SentenceBoundary` events (v7+) with per-sentence timing — fed directly into the viseme scheduler for accurate lip sync
- Requires ffmpeg for MP3→WAV conversion

### MockTTS
- No network, no ffmpeg needed
- Generates a 220 Hz sine wave
- Returns per-word timings (equal split)
- Useful for testing the pipeline without TTS dependencies

---

## Viseme Pipeline

```
text input
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  SpeechSynthesizer  (speech_synthesizer.py)         │
│                                                     │
│  1. Try ElevenLabs → edge-tts → MockTTS            │
│  2. Receive WAV + timing events                     │
│  3. Phonemize text (CMU dict → ARPABET)             │
│  4. Schedule visemes                                │
│  5. Build sentence events                           │
└─────────────┬───────────────────────────────────────┘
              │
    ┌─────────▼────────────────────────────┐
    │  Phonemizer  (phonemizer/)           │
    │  text → [(word, [ARPABET phones])]   │
    │  CMU dict lookup + rule fallback     │
    └─────────┬────────────────────────────┘
              │
    ┌─────────▼────────────────────────────┐
    │  VisemeScheduler  (viseme/)          │
    │  Assigns each phoneme a timestamp    │
    │  within its word/sentence window     │
    │                                      │
    │  Timing modes:                       │
    │   approximate — equal per phoneme    │
    │   enhanced    — weighted by category │
    │    (vowels 1.5×, stops 0.6×, …)     │
    │                                      │
    │  Deduplicates consecutive same IDs   │
    │  Inserts silence at sentence ends    │
    └─────────┬────────────────────────────┘
              │
    SpeechSynthesisResult
    (audio_data, duration_ms, viseme_events, sentence_events)
              │
    ┌─────────▼────────────────────────────┐
    │  server.py  — HTTP /speak            │
    │  Serialises to JSON response         │
    └──────────────────────────────────────┘
```

### Timing modes

Controlled by `timing_mode` in `SpeechSynthesizer` (default: `enhanced` in the server):

| Mode | Description |
|------|-------------|
| `approximate` | Each phoneme in a word gets an equal slice of the word's time window |
| `enhanced` | Phonemes weighted by articulatory category: vowels 1.5×, stops 0.6×, fricatives 1.1×, nasals 0.8× |

### Live parameter tuning

The server reloads `lipsync_params.json` on every `/speak` request — no restart needed to test parameter changes. Parameters:

| Key | Default | Effect |
|-----|---------|--------|
| `global_offset_ms` | `0.0` | Shift all viseme timestamps by ±N ms |
| `time_scale` | `1.0` | Stretch/compress the entire timeline |
| `vowel_weight` | `1.5` | Enhanced-mode vowel duration weight |
| `consonant_weight` | `0.6` | Enhanced-mode stop duration weight |

---

## Architecture & File Layout

```
sound_engine/tts/
├── __init__.py                  # Exports SpeechSynthesizer, VisemeEvent, SentenceEvent
├── server.py                   # HTTP server — entry point
├── speech_synthesizer.py       # Main orchestrator (provider → phonemizer → scheduler)
├── providers/
│   ├── elevenlabs_provider.py  # Paid TTS, MP3 output, no boundary events
│   ├── edge_tts_provider.py    # Free TTS, MP3 + SentenceBoundary events
│   └── mock_tts.py             # Offline sine-wave fallback
├── phonemizer/
│   ├── phonemizer.py           # Tokenize + CMU dict lookup
│   ├── cmu_dict.py             # NLTK CMU dictionary wrapper (lazy-loaded)
│   └── rule_fallback.py        # Letter-to-phoneme rules when dict misses
├── viseme/
│   ├── arpabet_to_viseme.py    # ARPABET → Azure viseme ID table + weights
│   └── viseme_scheduler.py     # Distributes phonemes across time windows
└── examples/
    └── usage.py                # End-to-end demo: synthesize + print viseme table
```

Shared files that remain at `sound_engine/` root (used by both TTS and other tools):

| File | Purpose |
|------|---------|
| `_types.py` | `VisemeEvent`, `SentenceEvent`, `SpeechSynthesisResult` dataclasses |
| `wav/wav_encoder.py` | WAV encode/decode + MP3→WAV via pydub |
| `param_config.py` | `lipsync_params.json` read/write |
| `audio_analyzer.py` | WAV energy analysis |

---

## Tick Convention

`viseme_events[i].audio_offset` (internal, before serialisation) is in **100-nanosecond ticks**:

```
offset_ticks = time_ms × 10,000
```

This matches Azure Cognitive Services SDK conventions and `AzureSpeechManager.cs` in the Unity project. The HTTP response converts to milliseconds (`time_ms`) for readability. **Do not change the internal tick unit** — Unity compatibility depends on it.

---

## Quick Smoke Test (offline, no ffmpeg)

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

## Full Test (needs internet + ffmpeg)

```bash
.venv/Scripts/python sound_engine/tts/examples/usage.py approximate
.venv/Scripts/python sound_engine/tts/examples/usage.py enhanced
```

## Unity Integration

Unity's `AzureSpeechManager.cs` POSTs to `/speak`, decodes the WAV from base64, builds an `AudioClip` and `VisemeTimeline`, then calls `lipSyncController.Play(timeline, clip)`.

Subscribe to sentence events in Unity:
```csharp
lipSyncController.OnSentenceFinished += sentence => {
    // send complete sentence to AI agent
};
```
