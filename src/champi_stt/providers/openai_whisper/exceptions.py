"""Exceptions for the OpenAI Whisper STT provider."""


class OpenAIWhisperError(Exception):
    """Base exception for OpenAI Whisper provider errors."""


class OpenAIWhisperAuthError(OpenAIWhisperError):
    """Raised when the API key is missing or invalid."""


class OpenAIWhisperAPIError(OpenAIWhisperError):
    """Raised when the OpenAI API returns an error."""


class OpenAIWhisperFileSizeError(OpenAIWhisperError):
    """Raised when the audio file exceeds the 25 MB limit."""
