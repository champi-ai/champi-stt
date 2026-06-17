"""Kokoro provider exceptions."""


class KokoroError(Exception):
    """Base exception for Kokoro provider errors."""


class KokoroNotInstalledError(KokoroError):
    """Raised when the kokoro package is not installed."""


class KokoroTranscriptionError(KokoroError):
    """Raised when the Kokoro pipeline fails to transcribe audio."""
