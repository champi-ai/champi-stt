"""
Wake Word Detection System
==========================

Provides wake word/hotword detection for voice assistants.

Supported engines:
- WhisperWakeWord (uses WhisperLive STT)
- Porcupine (high accuracy, requires API key)
- Vosk (offline, no API key required)
"""

from champi_stt.assistant.wakeword.base import (
    BaseWakeWordDetector,
    BaseWakeWordEngine,
    WakeWordConfig,
    WakeWordEvent,
)
from champi_stt.assistant.wakeword.vosk import VoskWakeWord
from champi_stt.assistant.wakeword.whisper import WhisperWakeWordDetector

__all__ = [
    "BaseWakeWordDetector",
    "BaseWakeWordEngine",
    "VoskWakeWord",
    "WakeWordConfig",
    "WakeWordEvent",
    "WhisperWakeWordDetector",
]
