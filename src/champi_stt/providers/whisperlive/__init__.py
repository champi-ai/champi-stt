"""
WhisperLive STT Provider
=========================

Local speech-to-text processing using WhisperLive's optimized faster-whisper backend.
"""

from champi_stt.providers.whisperlive.config import WhisperLiveConfig
from champi_stt.providers.whisperlive.provider import WhisperLiveSTTProvider
from champi_stt.providers.whisperlive.transcriber import WhisperLiveTranscriber
from champi_stt.providers.whisperlive.models import ModelManager, ModelCacheManager, DeviceManager
from champi_stt.providers.whisperlive.events import STTSignalManager
from champi_stt.providers.whisperlive.exceptions import (
    WhisperError,
    WhisperInitializationError,
    WhisperModelError,
    WhisperTranscriptionError,
    WhisperAudioError,
    WhisperConfigurationError,
    WhisperFileError,
    WhisperDeviceError,
)
from champi_stt.providers.whisperlive.enums import (
    STTEventTypes, LifecycleEvents, ModelEvents, ProcessingEvents,
    TelemetryEvents, AudioFormat, ModelSize, DeviceType, ComputeType,
    ResponseFormat, TaskType
)

__all__ = [
    # Core components
    "WhisperLiveConfig",
    "WhisperLiveSTTProvider",
    "WhisperLiveTranscriber",

    # Model management
    "ModelManager",
    "ModelCacheManager",
    "DeviceManager",

    # Event system
    "STTSignalManager",

    # Exceptions
    "WhisperError",
    "WhisperInitializationError",
    "WhisperModelError",
    "WhisperTranscriptionError",
    "WhisperAudioError",
    "WhisperConfigurationError",
    "WhisperFileError",
    "WhisperDeviceError",

    # Enums
    "STTEventTypes",
    "LifecycleEvents",
    "ModelEvents",
    "ProcessingEvents",
    "TelemetryEvents",
    "AudioFormat",
    "ModelSize",
    "DeviceType",
    "ComputeType",
    "ResponseFormat",
    "TaskType",
]
