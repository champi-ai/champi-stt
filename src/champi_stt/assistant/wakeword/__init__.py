"""
Wake Word Detection System
==========================

Provides wake word/hotword detection for voice assistants.

Supported engines:
- WhisperWakeWord (recommended, uses WhisperLive STT)
- OpenWakeWord (free and open source)
- Vosk (open source, general ASR)
"""

from champi_stt.assistant.wakeword.base import (
    BaseWakeWordDetector,
    BaseWakeWordEngine,
    WakeWordConfig,
    WakeWordEvent,
)
from champi_stt.assistant.wakeword.whisper import WhisperWakeWordDetector

__all__ = [
    "BaseWakeWordDetector",
    "BaseWakeWordEngine",
    "WakeWordConfig",
    "WakeWordEvent",
    "WhisperWakeWordDetector",
]
