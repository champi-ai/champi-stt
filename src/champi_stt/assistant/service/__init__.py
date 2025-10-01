"""
Voice Assistant Service/Daemon
==============================

System service for continuous voice assistant operation.

Features:
- Continuous wake word listening
- Voice command processing
- System service integration (systemd, launchd, Windows)
"""

from champi_stt.assistant.service.daemon import AssistantService, ServiceState
from champi_stt.assistant.service.config import AssistantConfig

__all__ = [
    "AssistantService",
    "ServiceState",
    "AssistantConfig",
]
