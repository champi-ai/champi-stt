"""
WhisperLive STT Provider
=========================

Local speech-to-text processing using WhisperLive's optimized faster-whisper backend.
"""

from champi_stt.providers.whisperlive.config import WhisperLiveConfig
from champi_stt.providers.whisperlive.enums import (
    AudioFormat,
    ComputeType,
    DeviceType,
    LifecycleEvents,
    ModelEvents,
    ModelSize,
    ProcessingEvents,
    ResponseFormat,
    STTEventTypes,
    TaskType,
    TelemetryEvents,
)
from champi_stt.providers.whisperlive.events import STTSignalManager
from champi_stt.providers.whisperlive.exceptions import (
    WhisperAudioError,
    WhisperConfigurationError,
    WhisperDeviceError,
    WhisperError,
    WhisperFileError,
    WhisperInitializationError,
    WhisperModelError,
    WhisperTranscriptionError,
)
from champi_stt.providers.whisperlive.models import (
    DeviceManager,
    ModelCacheManager,
    ModelManager,
)
from champi_stt.providers.whisperlive.provider import WhisperLiveSTTProvider
from champi_stt.providers.whisperlive.transcriber import WhisperLiveTranscriber

__all__ = [
    "AudioFormat",
    "ComputeType",
    "DeviceManager",
    "DeviceType",
    "LifecycleEvents",
    "ModelCacheManager",
    "ModelEvents",
    "ModelManager",
    "ModelSize",
    "ProcessingEvents",
    "ResponseFormat",
    "STTEventTypes",
    "STTSignalManager",
    "TaskType",
    "TelemetryEvents",
    "WhisperAudioError",
    "WhisperConfigurationError",
    "WhisperDeviceError",
    "WhisperError",
    "WhisperFileError",
    "WhisperInitializationError",
    "WhisperLiveConfig",
    "WhisperLiveSTTProvider",
    "WhisperLiveTranscriber",
    "WhisperModelError",
    "WhisperTranscriptionError",
]
