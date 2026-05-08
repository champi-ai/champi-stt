"""Configuration for the OpenAI Whisper STT provider."""

import os
from dataclasses import dataclass, field


@dataclass
class OpenAIWhisperConfig:
    """Configuration for the OpenAI Whisper API provider."""

    api_key: str = ""
    model: str = "whisper-1"
    language: str | None = None
    temperature: float = 0.0
    base_url: str | None = None

    save_transcriptions: bool = False
    transcriptions_dir: str = "~/.cache/champi-stt/transcriptions"

    # Maximum file size in bytes (25 MB OpenAI limit)
    max_file_size_bytes: int = 25 * 1024 * 1024

    # Extra headers forwarded to the HTTP client
    extra_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY", "")

    @classmethod
    def from_env(cls) -> "OpenAIWhisperConfig":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_WHISPER_MODEL", "whisper-1"),
            language=os.getenv("OPENAI_WHISPER_LANGUAGE"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )
