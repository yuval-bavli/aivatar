"""Test client for the STT WebSocket server.

Streams a .wav file to the server in real-time, simulating a microphone.
Prints all messages received (VAD events and transcript results).

Usage:
    .venv/Scripts/python -m sound_engine.stt.test_client audio.wav
    .venv/Scripts/python -m sound_engine.stt.test_client audio.wav --language he
    .venv/Scripts/python -m sound_engine.stt.test_client audio.wav --language mixed
    .venv/Scripts/python -m sound_engine.stt.test_client audio.wav --url ws://localhost:8765/ws/transcribe
"""

import argparse
import asyncio
import json
import sys
import wave

import websockets

CHUNK_MS = 100                  # simulate ~100ms mic chunks
SERVER_URL = "ws://localhost:8765/ws/transcribe"
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2                # 16-bit = 2 bytes per sample
CHANNELS = 1


def _load_wav_as_s16le(path: str) -> bytes:
    """Read a WAV file and return raw PCM bytes at 16kHz mono s16le.

    Raises ValueError if the file has unexpected format.
    We do not resample — the file must already be 16kHz mono 16-bit.
    If the file has a different sample rate or channel count, this function
    prints a warning and the server will produce incorrect results.
    """
    with wave.open(path, "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()

        if framerate != SAMPLE_RATE:
            print(f"WARNING: WAV is {framerate}Hz but server expects {SAMPLE_RATE}Hz. "
                  "Transcription quality may suffer.", file=sys.stderr)
        if channels != CHANNELS:
            print(f"WARNING: WAV has {channels} channels but server expects mono.",
                  file=sys.stderr)
        if sampwidth != SAMPLE_WIDTH:
            print(f"WARNING: WAV has {sampwidth}-byte samples but server expects 16-bit.",
                  file=sys.stderr)

        raw = wf.readframes(n_frames)

    duration_s = n_frames / framerate
    print(f"Loaded: {path}")
    print(f"  Duration: {duration_s:.2f}s | {framerate}Hz | {channels}ch | {sampwidth*8}-bit")
    print(f"  Total bytes: {len(raw):,}")
    return raw


async def _stream(url: str, pcm_bytes: bytes, language: str) -> None:
    chunk_samples = int(SAMPLE_RATE * CHUNK_MS / 1000)
    chunk_bytes = chunk_samples * SAMPLE_WIDTH
    total_chunks = (len(pcm_bytes) + chunk_bytes - 1) // chunk_bytes

    print(f"\nConnecting to {url} ...")
    async with websockets.connect(url + f"?language={language}") as ws:
        print(f"Connected. Streaming {total_chunks} chunks ({CHUNK_MS}ms each)...\n")

        # Send an optional config message to confirm language on the server side
        await ws.send(json.dumps({"type": "config", "language": language}))

        # Task: stream audio
        async def _send_audio():
            for i in range(0, len(pcm_bytes), chunk_bytes):
                chunk = pcm_bytes[i:i + chunk_bytes]
                await ws.send(chunk)
                await asyncio.sleep(CHUNK_MS / 1000)
            # Signal we're done sending by waiting a couple extra seconds
            # for any final transcript to arrive
            await asyncio.sleep(2.0)

        # Task: receive and print messages
        transcript_count = 0

        async def _receive():
            nonlocal transcript_count
            async for raw in ws:
                if isinstance(raw, bytes):
                    continue  # server doesn't send binary, but be safe
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    print(f"[raw] {raw}")
                    continue

                msg_type = msg.get("type", "?")
                if msg_type == "vad_event":
                    event = msg.get("event", "?")
                    print(f"  [VAD] {event}")
                elif msg_type == "transcript":
                    transcript_count += 1
                    text = msg.get("text", "")
                    lang = msg.get("language", "?")
                    dur = msg.get("duration_ms", 0)
                    inf = msg.get("inference_ms", 0)
                    print(f"\n  [TRANSCRIPT #{transcript_count}] ({lang}, {dur}ms audio, "
                          f"{inf}ms inference)")
                    print(f"  >>> {text!r}\n")
                elif msg_type == "error":
                    print(f"  [ERROR] {msg.get('message', msg)}", file=sys.stderr)
                else:
                    print(f"  [{msg_type}] {msg}")

        try:
            await asyncio.gather(
                _send_audio(),
                _receive(),
            )
        except websockets.exceptions.ConnectionClosedOK:
            pass

    print(f"\nDone. Received {transcript_count} transcript(s).")


def main():
    parser = argparse.ArgumentParser(description="STT test client — streams a WAV file to the server")
    parser.add_argument("wav_file", help="Path to a 16kHz mono 16-bit WAV file")
    parser.add_argument("--language", default="en", choices=["en", "he", "mixed"],
                        help="Transcription language (default: en)")
    parser.add_argument("--url", default=SERVER_URL,
                        help=f"WebSocket URL (default: {SERVER_URL})")
    args = parser.parse_args()

    pcm_bytes = _load_wav_as_s16le(args.wav_file)
    asyncio.run(_stream(args.url, pcm_bytes, args.language))


if __name__ == "__main__":
    main()
