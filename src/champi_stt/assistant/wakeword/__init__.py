"""
Wake Word Detection System
==========================

Provides wake word/hotword detection for voice assistants.

Supported engines:
- Porcupine (recommended, commercial-friendly)
- Vosk (open source, small models)
- Snowboy (legacy, deprecated)
"""

from champi_stt.assistant.wakeword.base import BaseWakeWordEngine, WakeWordConfig

__all__ = [
    "BaseWakeWordEngine",
    "WakeWordConfig",
]
