"""OpenAI Whisper API STT provider."""

from champi_stt.providers.openai_whisper.config import OpenAIWhisperConfig
from champi_stt.providers.openai_whisper.exceptions import (
    OpenAIWhisperAPIError,
    OpenAIWhisperAuthError,
    OpenAIWhisperError,
    OpenAIWhisperFileSizeError,
)
from champi_stt.providers.openai_whisper.provider import OpenAIWhisperProvider

__all__ = [
    "OpenAIWhisperAPIError",
    "OpenAIWhisperAuthError",
    "OpenAIWhisperConfig",
    "OpenAIWhisperError",
    "OpenAIWhisperFileSizeError",
    "OpenAIWhisperProvider",
]
