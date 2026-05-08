"""Exceptions for the Deepgram STT provider."""


class DeepgramError(Exception):
    """Base exception for Deepgram provider errors."""


class DeepgramAuthError(DeepgramError):
    """Raised when the API key is missing or invalid."""


class DeepgramAPIError(DeepgramError):
    """Raised when the Deepgram API returns an error response."""
