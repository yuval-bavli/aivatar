"""Live microphone test client for the STT WebSocket server.

On first run (or when the saved device is no longer available), prompts you to
choose a microphone and language. Your choice is saved to mic_client_state.json
next to this file. On subsequent runs, the saved choice is the default — just
press Enter to accept it.

Usage:
    .venv/Scripts/python -m sound_engine.stt.mic_client
    .venv/Scripts/python -m sound_engine.stt.mic_client --reset   # force re-selection
    .venv/Scripts/python -m sound_engine.stt.mic_client --url ws://localhost:8765/ws/transcribe

Press Ctrl+C to stop streaming.
"""

import argparse
import asyncio
import json
import os
import queue
import sys

import numpy as np
import sounddevice as sd
import websockets

SERVER_URL = "ws://localhost:8765/ws/transcribe"
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_MS = 64
DTYPE = "int16"

STATE_FILE = os.path.join(os.path.dirname(__file__), "mic_client_state.json")
SUPPORTED_LANGUAGES = {"en": "English", "he": "Hebrew", "mixed": "Mixed (Hebrew/English auto-detect)"}


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_state(device_index: int, device_name: str, language: str) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump({"device_index": device_index,
                   "device_name": device_name,
                   "language": language}, f, indent=2)


# ---------------------------------------------------------------------------
# Device discovery
# ---------------------------------------------------------------------------

def _get_input_devices() -> list[dict]:
    """Return list of available input devices with index, name, channels."""
    devices = []
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            devices.append({
                "index": i,
                "name": dev["name"],
                "channels": dev["max_input_channels"],
                "sample_rate": int(dev["default_samplerate"]),
            })
    return devices


def _find_saved_device(devices: list[dict], state: dict) -> int | None:
    """Return the list position of the previously saved device, or None."""
    saved_name = state.get("device_name")
    saved_idx = state.get("device_index")
    if saved_name is None:
        return None
    for pos, dev in enumerate(devices):
        if dev["index"] == saved_idx and dev["name"] == saved_name:
            return pos
    return None


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def _prompt_device(devices: list[dict], saved_pos: int | None) -> dict:
    print("\nAvailable microphones:")
    for pos, dev in enumerate(devices):
        marker = " (last used)" if pos == saved_pos else ""
        print(f"  [{pos + 1}] {dev['name']}{marker}")

    default_label = f"{saved_pos + 1}" if saved_pos is not None else "1"
    while True:
        raw = input(f"\nSelect microphone [default: {default_label}]: ").strip()
        if raw == "":
            choice = (saved_pos if saved_pos is not None else 0)
        else:
            try:
                choice = int(raw) - 1
            except ValueError:
                print("  Enter a number.")
                continue
        if 0 <= choice < len(devices):
            return devices[choice]
        print(f"  Enter a number between 1 and {len(devices)}.")


def _prompt_language(saved_lang: str | None) -> str:
    options = list(SUPPORTED_LANGUAGES.items())  # [("en", "English"), ("he", "Hebrew")]
    print("\nLanguage:")
    for pos, (code, name) in enumerate(options):
        marker = " (last used)" if code == saved_lang else ""
        print(f"  [{pos + 1}] {name}{marker}")

    saved_pos = next((i for i, (c, _) in enumerate(options) if c == saved_lang), 0)
    default_label = str(saved_pos + 1)
    while True:
        raw = input(f"Select language [default: {default_label}]: ").strip()
        if raw == "":
            return options[saved_pos][0]
        try:
            choice = int(raw) - 1
        except ValueError:
            print("  Enter a number.")
            continue
        if 0 <= choice < len(options):
            return options[choice][0]
        print(f"  Enter 1 or 2.")


def _select_config(reset: bool) -> tuple[dict, str]:
    """Prompt for (or load from state) device + language. Returns (device, language)."""
    devices = _get_input_devices()
    if not devices:
        print("No input devices found.", file=sys.stderr)
        sys.exit(1)

    state = {} if reset else _load_state()
    saved_pos = _find_saved_device(devices, state)
    saved_lang = state.get("language")

    # If state is valid and not resetting, show what we'll use and let user confirm
    if not reset and saved_pos is not None and saved_lang is not None:
        dev = devices[saved_pos]
        lang_name = SUPPORTED_LANGUAGES.get(saved_lang, saved_lang)
        print(f"\nUsing saved config:")
        print(f"  Microphone : {dev['name']}")
        print(f"  Language   : {lang_name}")
        raw = input("Press Enter to continue, or 'c' to change: ").strip().lower()
        if raw != "c":
            return dev, saved_lang
        # Fall through to interactive prompt
        saved_pos = _find_saved_device(devices, state)  # re-derive for prompts

    device = _prompt_device(devices, saved_pos)
    language = _prompt_language(saved_lang)
    _save_state(device["index"], device["name"], language)
    return device, language


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

async def run(device: dict, language: str, url: str) -> None:
    chunk_samples = int(SAMPLE_RATE * CHUNK_MS / 1000)
    audio_queue: queue.Queue[bytes] = queue.Queue()

    def mic_callback(indata: np.ndarray, frames: int, time, status):
        if status:
            print(f"[mic] {status}", file=sys.stderr)
        audio_queue.put(indata[:, 0].tobytes())

    ws_url = f"{url}?language={language}"
    lang_name = SUPPORTED_LANGUAGES.get(language, language)
    print(f"\nConnecting to {ws_url} ...")

    async with websockets.connect(ws_url) as ws:
        print(f"Connected. Speak in {lang_name} — Ctrl+C to stop.\n")

        async def send_audio():
            while True:
                chunks = []
                try:
                    while True:
                        chunks.append(audio_queue.get_nowait())
                except queue.Empty:
                    pass
                for chunk in chunks:
                    await ws.send(chunk)
                await asyncio.sleep(CHUNK_MS / 1000 / 2)

        async def receive_messages():
            async for raw in ws:
                if isinstance(raw, bytes):
                    continue
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")
                if msg_type == "vad_event":
                    event = msg.get("event")
                    if event == "speech_start":
                        print("  \033[2m[listening...]\033[0m", end="", flush=True)
                    elif event == "speech_end":
                        print("  \033[2m[transcribing...]\033[0m", end="", flush=True)
                elif msg_type == "transcript":
                    text = msg.get("text", "").strip()
                    inf = msg.get("inference_ms", 0)
                    print(f"\r>>> {text}  \033[2m({inf:.0f}ms)\033[0m")
                elif msg_type == "error":
                    print(f"\n[ERROR] {msg.get('message')}", file=sys.stderr)

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=chunk_samples,
            device=device["index"],
            callback=mic_callback,
        )
        with stream:
            try:
                await asyncio.gather(send_audio(), receive_messages())
            except websockets.exceptions.ConnectionClosedOK:
                pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Live mic STT client")
    parser.add_argument("--reset", action="store_true",
                        help="Ignore saved config and re-select mic/language")
    parser.add_argument("--url", default=SERVER_URL,
                        help=f"WebSocket server URL (default: {SERVER_URL})")
    args = parser.parse_args()

    device, language = _select_config(args.reset)

    try:
        asyncio.run(run(device, language, args.url))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
