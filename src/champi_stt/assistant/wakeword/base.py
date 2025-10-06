"""
Base wake word detection engine interface
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional, Any
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class WakeWordConfig:
    """Configuration for wake word detection"""

    # Wake word settings
    keywords: list[str]  # List of wake words to detect
    sensitivity: float = 0.5  # Detection sensitivity (0.0-1.0)

    # Audio settings
    sample_rate: int = 16000  # Sample rate for wake word detection
    frame_length_ms: int = 30  # Audio frame length in milliseconds

    # Model/Engine settings
    model_path: Optional[str] = None  # Path to custom wake word model
    access_key: Optional[str] = None  # API key (for Porcupine)

    # Behavior settings
    auto_reset: bool = True  # Auto-reset after detection
    cooldown_ms: int = 1000  # Cooldown period after detection (ms)


class BaseWakeWordEngine(ABC):
    """
    Abstract base class for wake word detection engines.

    All wake word engines (Porcupine, Vosk, Snowboy) must implement this interface.
    """

    def __init__(self, config: WakeWordConfig):
        """
        Initialize wake word engine.

        Args:
            config: Wake word configuration
        """
        self.config = config
        self._callback: Optional[Callable] = None
        self._initialized = False
        self._last_detection_time = 0

        logger.debug(f"Initializing {self.__class__.__name__} with keywords: {config.keywords}")

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the wake word engine.

        This may include:
        - Loading models
        - Validating API keys
        - Setting up audio processing
        """
        pass

    @abstractmethod
    async def process_audio(self, audio_chunk: np.ndarray) -> tuple[bool, Optional[str]]:
        """
        Process audio chunk for wake word detection.

        Args:
            audio_chunk: Audio data as numpy array (int16 or float32)

        Returns:
            Tuple of (detected, keyword):
            - detected: True if wake word detected
            - keyword: The detected keyword (None if not detected)
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup resources"""
        pass

    @property
    @abstractmethod
    def is_initialized(self) -> bool:
        """Check if engine is initialized and ready"""
        pass

    # Helper methods (can be used by implementations)

    def on_detection(self, callback: Callable[[str], Any]) -> None:
        """
        Register callback for wake word detection.

        Args:
            callback: Function to call when wake word detected.
                     Receives keyword as string argument.
        """
        self._callback = callback
        logger.debug(f"Registered detection callback: {callback.__name__}")

    async def _trigger_callback(self, keyword: str) -> None:
        """
        Trigger the registered callback if available.

        Args:
            keyword: The detected keyword
        """
        if self._callback:
            try:
                if asyncio.iscoroutinefunction(self._callback):
                    await self._callback(keyword)
                else:
                    self._callback(keyword)
                logger.info(f"✓ Wake word detected: '{keyword}'")
            except Exception as e:
                logger.error(f"Error in wake word callback: {e}")

    def _check_cooldown(self) -> bool:
        """
        Check if cooldown period has elapsed.

        Returns:
            True if detection is allowed (cooldown elapsed)
        """
        import time
        current_time = time.time() * 1000  # Convert to ms

        if current_time - self._last_detection_time < self.config.cooldown_ms:
            return False

        return True

    def _update_detection_time(self) -> None:
        """Update last detection timestamp"""
        import time
        self._last_detection_time = time.time() * 1000

    async def process_audio_with_callback(self, audio_chunk: np.ndarray) -> bool:
        """
        Process audio and automatically trigger callback if detected.

        Convenience method that combines process_audio and callback triggering.

        Args:
            audio_chunk: Audio data

        Returns:
            True if wake word detected
        """
        # Check cooldown
        if not self._check_cooldown():
            return False

        # Process audio
        detected, keyword = await self.process_audio(audio_chunk)

        if detected and keyword:
            self._update_detection_time()
            await self._trigger_callback(keyword)
            return True

        return False

    def get_frame_length_samples(self) -> int:
        """
        Get the required audio frame length in samples.

        Returns:
            Number of samples per frame
        """
        return int(self.config.sample_rate * self.config.frame_length_ms / 1000)


# Import asyncio at module level
import asyncio
