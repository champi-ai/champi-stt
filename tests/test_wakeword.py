"""Tests for wake word detection."""

import numpy as np
import pytest

from champi_stt.assistant.wakeword.base import (
    BaseWakeWordEngine,
    WakeWordConfig,
    WakeWordEvent,
)


class TestWakeWordEvent:
    """Tests for WakeWordEvent dataclass."""

    def test_event_creation(self):
        """Test creating a wake word event."""
        event = WakeWordEvent(
            keyword="computer", confidence=0.95, timestamp=1234567890.0
        )

        assert event.keyword == "computer"
        assert event.confidence == 0.95
        assert event.timestamp == 1234567890.0

    def test_event_default_confidence(self):
        """Test event with default confidence."""
        event = WakeWordEvent(keyword="alexa", timestamp=1234567890.0)

        assert event.confidence == 1.0


class TestWakeWordConfig:
    """Tests for WakeWordConfig."""

    def test_config_creation(self):
        """Test creating wake word config."""
        config = WakeWordConfig(
            keywords=["computer", "assistant"], sensitivity=0.7, audio_device_index=1
        )

        assert config.keywords == ["computer", "assistant"]
        assert config.sensitivity == 0.7
        assert config.audio_device_index == 1

    def test_config_default_values(self):
        """Test config with default values."""
        config = WakeWordConfig(keywords=["test"])

        assert config.keywords == ["test"]
        assert config.sensitivity == 0.5
        assert config.audio_device_index is None

    def test_config_empty_keywords_raises(self):
        """Test that empty keywords raises error."""
        with pytest.raises((ValueError, TypeError)):
            WakeWordConfig(keywords=[])


class ConcreteDetector(BaseWakeWordEngine):
    """Concrete detector for testing."""

    async def initialize(self) -> None:
        """Initialize detector."""
        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown detector."""
        self._initialized = False

    async def detect(self, audio_frame: np.ndarray) -> WakeWordEvent | None:
        """Mock detect."""
        # Simulate detection
        if np.any(audio_frame > 0):
            return WakeWordEvent(
                keyword=self.config.keywords[0],
                confidence=0.9,
                timestamp=1234567890.0,
            )
        return None


class TestBaseWakeWordEngine:
    """Tests for BaseWakeWordEngine abstract class."""

    def test_detector_initialization(self):
        """Test detector initialization."""
        config = WakeWordConfig(keywords=["test"])
        detector = ConcreteDetector(config)

        assert detector.config == config
        assert detector.keywords == ["test"]
        assert not detector.is_active

    @pytest.mark.asyncio
    async def test_detector_lifecycle(self):
        """Test detector initialize and shutdown."""
        config = WakeWordConfig(keywords=["test"])
        detector = ConcreteDetector(config)

        await detector.initialize()
        assert detector._initialized

        await detector.shutdown()
        assert not detector._initialized

    @pytest.mark.asyncio
    async def test_detector_context_manager(self):
        """Test detector as async context manager."""
        config = WakeWordConfig(keywords=["test"])
        detector = ConcreteDetector(config)

        async with detector:
            assert detector._initialized

        assert not detector._initialized

    @pytest.mark.asyncio
    async def test_detector_detect(self, sample_audio_data: np.ndarray):
        """Test detect method."""
        config = WakeWordConfig(keywords=["computer"])
        detector = ConcreteDetector(config)

        # Create audio with some signal
        audio = np.array([100, 200, 300], dtype=np.int16)
        result = await detector.detect(audio)

        assert result is not None
        assert isinstance(result, WakeWordEvent)
        assert result.keyword == "computer"

    @pytest.mark.asyncio
    async def test_detector_no_detection(self):
        """Test no detection with silence."""
        config = WakeWordConfig(keywords=["test"])
        detector = ConcreteDetector(config)

        # Silent audio
        audio = np.zeros(1000, dtype=np.int16)
        result = await detector.detect(audio)

        assert result is None

    def test_detector_sensitivity(self):
        """Test sensitivity property."""
        config = WakeWordConfig(keywords=["test"], sensitivity=0.8)
        detector = ConcreteDetector(config)

        assert detector.sensitivity == 0.8


# Note: Porcupine detector tests removed as implementation is deprecated
# OpenWakeWord is now the default wake word engine
# Tests for OpenWakeWord detector to be added when implementation is complete
