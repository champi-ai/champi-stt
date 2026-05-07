"""Signal manager for assistant IPC."""

from enum import Enum

from champi_signals import BaseSignalManager


class AssistantEventTypes(Enum):
    """Event type categories for assistant."""

    LIFECYCLE = "lifecycle"
    PROCESSING = "processing"
    STATE = "state"
    ERROR = "error"


class AssistantSignalManager(BaseSignalManager):
    """Signal manager for assistant events.

    Provides blinker signals for:
    - lifecycle: Assistant lifecycle events (startup, shutdown, etc.)
    - processing: Processing events (recording, transcribing, executing)
    - state: State change events (idle, awake, busy, etc.)
    - error: Error events
    """

    def __init__(self):
        """Initialize assistant signal manager with custom signals."""
        super().__init__()

        # Only setup signals once (singleton pattern)
        if not hasattr(self, "_assistant_signals_setup"):
            self.setup_custom_signals(
                {
                    "lifecycle": AssistantEventTypes,
                    "processing": AssistantEventTypes,
                    "state": AssistantEventTypes,
                    "error": AssistantEventTypes,
                }
            )
            self._assistant_signals_setup = True
