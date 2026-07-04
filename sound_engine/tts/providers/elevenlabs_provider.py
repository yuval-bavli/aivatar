"""Paid TTS via ElevenLabs REST API."""
import os
from typing import List, Optional, Tuple

from ...wav.wav_encoder import encode_raw_pcm_to_wav, get_duration_ms


class ElevenLabsProvider:
    """
    Calls ElevenLabs TTS API. Requires ELEVENLABS_API_KEY in environment or .env.
    Returns WAV bytes. No word-boundary events — falls back to equal timing distribution.
    """

    API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    SAMPLE_RATE = 16000
    # Model is env-overridable (e.g. eleven_flash_v2_5 for lowest latency).
    DEFAULT_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_v3")

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

        from ..expression import to_elevenlabs_v3
        styled_text = to_elevenlabs_v3(text)

        url = self.API_URL.format(voice_id=self.voice_id)
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/pcm",
        }
        payload = {
            "text": styled_text,
            "model_id": self.DEFAULT_MODEL,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.5,
                "use_speaker_boost": True,
            },
        }
        # Request raw 16 kHz PCM so we can wrap it directly — no MP3 decode,
        # no ffmpeg subprocess on the speech path.
        params = {"output_format": f"pcm_{self.SAMPLE_RATE}"}

        resp = requests.post(url, json=payload, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(
                f"ElevenLabs API error {resp.status_code}: {resp.text[:200]}"
            )

        wav_bytes = encode_raw_pcm_to_wav(resp.content, sample_rate=self.SAMPLE_RATE)
        duration_ms = get_duration_ms(wav_bytes)

        return wav_bytes, duration_ms, []
