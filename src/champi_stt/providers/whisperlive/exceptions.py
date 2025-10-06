"""
Custom exceptions for WhisperLive STT service.
"""


class WhisperError(Exception):
    """Base exception for all WhisperLive STT errors"""
    pass


class WhisperInitializationError(WhisperError):
    """Raised when provider initialization fails"""
    pass


class WhisperModelError(WhisperError):
    """Raised when model loading or operations fail"""
    pass


class WhisperTranscriptionError(WhisperError):
    """Raised when transcription fails"""
    pass


class WhisperAudioError(WhisperError):
    """Raised when audio recording or playback fails"""
    pass


class WhisperConfigurationError(WhisperError):
    """Raised when configuration is invalid"""
    pass


class WhisperFileError(WhisperError):
    """Raised when file operations fail"""
    pass


class WhisperDeviceError(WhisperError):
    """Raised when device operations fail"""
    pass
