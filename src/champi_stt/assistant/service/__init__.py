"""
Voice Assistant Service/Daemon
==============================

System service for continuous voice assistant operation.

Features:
- Continuous wake word listening
- Voice command processing
- System service integration (systemd, launchd, Windows)
"""

from champi_stt.assistant.service.config import AssistantConfig
from champi_stt.assistant.service.daemon import AssistantService, ServiceState

__all__ = [
    "AssistantConfig",
    "AssistantService",
    "ServiceState",
]
