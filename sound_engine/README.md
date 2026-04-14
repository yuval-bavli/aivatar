# sound_engine

Python TTS + viseme generation module. Drop-in replacement for Azure Cognitive Services that works without an Azure subscription. Produces WAV audio and Azure-compatible viseme events (IDs 0–14) for driving lip sync.

## Setup

```bash
pip install -r requirements.txt
```

ffmpeg is required for MP3→WAV conversion (used by edge-tts and ElevenLabs):

```bash
# Windows
winget install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

## Quick Start

```python
from sound_engine import SpeechSynthesizer

synth = SpeechSynthesizer()
result = synth.speak_text("Hello, my name is Aivatar.")

# result.audio_data   — WAV bytes
# result.duration_ms  — total duration in milliseconds
# result.viseme_events — List[VisemeEvent]

for ev in result.viseme_events:
    print(ev.viseme_id, ev.audio_offset / 10_000, "ms")
```

Async version:

```python
import asyncio
result = asyncio.run(synth.speak_text_async("Hello world"))
```

Viseme callback (fires per event, same as Azure SDK pattern):

```python
synth.viseme_received = lambda ev: print(ev.viseme_id, ev.audio_offset)
```

## TTS Providers

Providers are tried in this order:

| Priority | Provider | Requirement | Quality |
|----------|----------|-------------|---------|
| 1 | ElevenLabs | `ELEVENLABS_API_KEY` in `.env` or environment | Best |
| 2 | edge-tts | Internet connection + ffmpeg | Good (MS neural voices) |
| 3 | MockTTS | Nothing — stdlib only | 220 Hz sine tone |

Set `ELEVENLABS_API_KEY` in the `.env` file at the repo root to enable ElevenLabs.

To force a specific Edge voice:

```python
synth = SpeechSynthesizer(voice="en-US-GuyNeural")
```

## Timing Modes

```python
synth = SpeechSynthesizer(timing_mode='approximate')  # default: equal slices per phoneme
synth = SpeechSynthesizer(timing_mode='enhanced')     # vowels longer, stops shorter
```

- **approximate** — equal duration per phoneme within each word's time window
- **enhanced** — phoneme-category weights (vowels ×1.5, stops ×0.6), better lip sync feel

## Viseme IDs

| ID | Name | Phonemes |
|----|------|----------|
| 0 | sil | silence, H |
| 1 | PP | P B M |
| 2 | FF | F V |
| 3 | TH | TH DH |
| 4 | DD | T D |
| 5 | kk | K G |
| 6 | CH | CH JH SH ZH |
| 7 | SS | S Z |
| 8 | nn | N NG L |
| 9 | RR | R |
| 10 | aa | AA AE |
| 11 | E | EH EY |
| 12 | ih | IH IY Y |
| 13 | oh | AO OW AH AW |
| 14 | ou | UW UH OY W |

`audio_offset` is in 100-nanosecond ticks — same unit as Azure SDK (1 ms = 10,000 ticks).

## Phonemizer

Words are looked up in the CMU Pronouncing Dictionary (134k words, auto-downloaded from NLTK on first use). Unknown words fall back to letter-to-ARPABET rules (handles digraphs: ch, sh, th, ph, etc.).

## Module Structure

```
sound_engine/
├── __init__.py
├── types.py                    # VisemeEvent, SpeechSynthesisResult
├── speech_synthesizer.py       # Main class
├── tts/
│   ├── edge_tts_provider.py
│   ├── elevenlabs_provider.py
│   └── mock_tts.py
├── phonemizer/
│   ├── phonemizer.py
│   ├── cmu_dict.py
│   └── rule_fallback.py
├── viseme/
│   ├── arpabet_to_viseme.py
│   └── viseme_scheduler.py
├── wav/
│   └── wav_encoder.py
└── examples/
    └── usage.py
```

## Example Script

```bash
python examples/usage.py              # approximate timing, writes output.wav
python examples/usage.py enhanced     # enhanced timing
```
