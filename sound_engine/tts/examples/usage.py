"""End-to-end example: synthesize speech and print viseme table."""
import sys
import os

# Allow running as: python sound_engine/tts/examples/usage.py from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from sound_engine.tts import SpeechSynthesizer

TEXT = "Hello! My name is Aivatar. I am a talking avatar."


def main():
    timing_mode = sys.argv[1] if len(sys.argv) > 1 else 'approximate'
    print(f"[usage] timing_mode={timing_mode}")
    print(f"[usage] text: {TEXT!r}\n")

    synth = SpeechSynthesizer(timing_mode=timing_mode)
    result = synth.speak_text(TEXT)

    print(f"Duration: {result.duration_ms:.1f} ms")
    print(f"WAV size: {len(result.audio_data)} bytes")
    print(f"Viseme events: {len(result.viseme_events)}\n")

    print(f"{'#':>4}  {'viseme_id':>9}  {'offset_ms':>10}  {'offset_ticks':>14}")
    print("-" * 45)
    for i, ev in enumerate(result.viseme_events):
        ms = ev.audio_offset / 10_000.0
        print(f"{i:>4}  {ev.viseme_id:>9}  {ms:>10.1f}  {ev.audio_offset:>14}")

    # Verify monotonically increasing offsets
    offsets = [ev.audio_offset for ev in result.viseme_events]
    assert offsets == sorted(offsets), "ERROR: offsets not monotonically increasing!"
    print("\nOffsets are monotonically increasing.")

    # Write output WAV
    out_path = os.path.join(os.path.dirname(__file__), '..', 'output.wav')
    with open(out_path, 'wb') as f:
        f.write(result.audio_data)
    print(f"Wrote {out_path}")

    if timing_mode == 'enhanced':
        # Check vowel durations vs stops
        from sound_engine.tts.viseme.arpabet_to_viseme import VOWELS, STOPS
        from sound_engine.tts.phonemizer.phonemizer import Phonemizer
        ph = Phonemizer()
        words = ph.phonemize_words(TEXT)
        all_phones = [p for _, phones in words for p in phones]
        vowel_count = sum(1 for p in all_phones if p in VOWELS)
        stop_count = sum(1 for p in all_phones if p in STOPS)
        print(f"\nEnhanced mode: {vowel_count} vowels, {stop_count} stops in phoneme sequence")


if __name__ == "__main__":
    main()
