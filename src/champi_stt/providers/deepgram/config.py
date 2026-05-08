"""Configuration for the Deepgram STT provider."""

import os
from dataclasses import dataclass


@dataclass
class DeepgramConfig:
    """Configuration for the Deepgram REST API provider."""

    api_key: str = ""

    # Model tier: "nova-2", "nova", "enhanced", "base", "whisper"
    model: str = "nova-2"

    language: str | None = None
    smart_format: bool = True
    punctuate: bool = True
    diarize: bool = False
    utterances: bool = False

    # Deepgram API endpoint (override for on-prem)
    base_url: str = "https://api.deepgram.com/v1"

    timeout_seconds: float = 60.0

    save_transcriptions: bool = False
    transcriptions_dir: str = "~/.cache/champi-stt/transcriptions"

    def __post_init__(self) -> None:
        if not self.api_key:
            self.api_key = os.getenv("DEEPGRAM_API_KEY", "")

    @classmethod
    def from_env(cls) -> "DeepgramConfig":
        return cls(
            api_key=os.getenv("DEEPGRAM_API_KEY", ""),
            model=os.getenv("DEEPGRAM_MODEL", "nova-2"),
            language=os.getenv("DEEPGRAM_LANGUAGE"),
        )
