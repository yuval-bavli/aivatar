"""Paid TTS via ElevenLabs REST API."""
import os
from typing import List, Optional, Tuple

from ..wav.wav_encoder import encode_raw_pcm_to_wav, get_duration_ms


class ElevenLabsProvider:
    """
    Calls ElevenLabs TTS API. Requires ELEVENLABS_API_KEY in environment or .env.
    Returns WAV bytes. No word-boundary events — falls back to equal timing distribution.
    """

    API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    SAMPLE_RATE = 16000

    def __init__(self, api_key: Optional[str] = None, voice_id: str = DEFAULT_VOICE_ID):
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
        self.voice_id = voice_id
        if not self.api_key:
            raise ValueError(
                "ElevenLabs API key not found. Set ELEVENLABS_API_KEY in .env or environment."
            )

    def synthesize(self, text: str) -> Tuple[bytes, float, List]:
        """
        Returns:
            (wav_bytes, duration_ms, [])  # no word timings
        """
        try:
            import requests
        except ImportError:
            raise RuntimeError("requests is not installed. Run: pip install requests")

        url = self.API_URL.format(voice_id=self.voice_id)
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(
                f"ElevenLabs API error {resp.status_code}: {resp.text[:200]}"
            )

        # ElevenLabs returns MP3 by default
        mp3_bytes = resp.content
        from ..wav.wav_encoder import mp3_to_wav
        wav_bytes = mp3_to_wav(mp3_bytes, sample_rate=self.SAMPLE_RATE)
        duration_ms = get_duration_ms(wav_bytes)

        return wav_bytes, duration_ms, []
