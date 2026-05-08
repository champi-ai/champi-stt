"""AssemblyAI provider exceptions."""


class AssemblyAIError(Exception):
    """Base exception for AssemblyAI provider errors."""


class AssemblyAIAuthError(AssemblyAIError):
    """Raised when the API key is missing or invalid."""


class AssemblyAIConnectionError(AssemblyAIError):
    """Raised when the WebSocket connection cannot be established."""


class AssemblyAIStreamingError(AssemblyAIError):
    """Raised when a streaming transcription error occurs."""
