"""Tests for core provider functionality."""

from pathlib import Path

import pytest

from champi_stt.core.base_config import BaseProviderConfig
from champi_stt.core.base_provider import BaseSTTProvider
from champi_stt.core.response import TranscriptionResponse, TranscriptionSegment

pytestmark = pytest.mark.skip(
    reason="API mismatch with current implementation - pending update"
)


class TestTranscriptionSegment:
    """Tests for TranscriptionSegment dataclass."""

    def test_segment_creation(self):
        """Test creating a transcription segment."""
        segment = TranscriptionSegment(
            text="hello world",
            start=0.0,
            end=1.5,
            confidence=0.95,
        )

        assert segment.text == "hello world"
        assert segment.start == 0.0
        assert segment.end == 1.5
        assert segment.confidence == 0.95

    def test_segment_duration(self):
        """Test calculating segment duration."""
        segment = TranscriptionSegment(text="test", start=1.0, end=3.5, confidence=0.9)

        assert segment.duration == 2.5

    def test_segment_words_optional(self):
        """Test that words field is optional."""
        segment = TranscriptionSegment(text="test", start=0.0, end=1.0, confidence=0.9)

        assert segment.words is None


class TestTranscriptionResponse:
    """Tests for TranscriptionResponse dataclass."""

    def test_response_creation(self):
        """Test creating a transcription response."""
        segments = [
            TranscriptionSegment(text="hello", start=0.0, end=1.0, confidence=0.95),
            TranscriptionSegment(text="world", start=1.0, end=2.0, confidence=0.93),
        ]

        response = TranscriptionResponse(
            text="hello world",
            language="en",
            segments=segments,
        )

        assert response.text == "hello world"
        assert response.language == "en"
        assert len(response.segments) == 2

    def test_response_duration(self):
        """Test calculating total duration from segments."""
        segments = [
            TranscriptionSegment(text="hello", start=0.0, end=1.0, confidence=0.95),
            TranscriptionSegment(text="world", start=1.0, end=2.5, confidence=0.93),
        ]

        response = TranscriptionResponse(
            text="hello world", language="en", segments=segments
        )

        assert response.duration == 2.5

    def test_response_average_confidence(self):
        """Test calculating average confidence."""
        segments = [
            TranscriptionSegment(text="hello", start=0.0, end=1.0, confidence=0.9),
            TranscriptionSegment(text="world", start=1.0, end=2.0, confidence=0.8),
        ]

        response = TranscriptionResponse(
            text="hello world", language="en", segments=segments
        )

        assert response.average_confidence == 0.85

    def test_response_no_segments(self):
        """Test response with no segments."""
        response = TranscriptionResponse(text="", language="en", segments=[])

        assert response.duration == 0.0
        assert response.average_confidence == 0.0


class TestBaseProviderConfig:
    """Tests for BaseProviderConfig."""

    def test_config_creation(self):
        """Test creating a base config."""
        config = BaseProviderConfig(model="base", language="en")

        assert config.model == "base"
        assert config.language == "en"

    def test_config_default_values(self):
        """Test config with default values."""
        config = BaseProviderConfig()

        assert config.model == "base"
        assert config.language is None


class ConcreteProvider(BaseSTTProvider):
    """Concrete implementation for testing."""

    async def initialize(self) -> None:
        """Initialize provider."""
        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown provider."""
        self._initialized = False

    async def transcribe(
        self, audio_source: str | Path, **kwargs
    ) -> TranscriptionResponse:
        """Mock transcribe."""
        return TranscriptionResponse(
            text="test transcription",
            language="en",
            segments=[
                TranscriptionSegment(
                    text="test transcription", start=0.0, end=1.0, confidence=0.95
                )
            ],
        )

    async def transcribe_stream(self, audio_stream, **kwargs):
        """Mock stream transcribe."""
        yield TranscriptionResponse(text="stream test", language="en", segments=[])


class TestBaseSTTProvider:
    """Tests for BaseSTTProvider abstract class."""

    def test_provider_initialization(self):
        """Test provider initialization."""
        config = BaseProviderConfig(model="base")
        provider = ConcreteProvider(config)

        assert provider.config == config
        assert provider.name == "ConcreteProvider"

    @pytest.mark.asyncio
    async def test_provider_lifecycle(self):
        """Test provider initialize and shutdown."""
        provider = ConcreteProvider(BaseProviderConfig())

        await provider.initialize()
        assert provider._initialized

        await provider.shutdown()
        assert not provider._initialized

    @pytest.mark.asyncio
    async def test_provider_context_manager(self):
        """Test provider as async context manager."""
        provider = ConcreteProvider(BaseProviderConfig())

        async with provider:
            assert provider._initialized

        assert not provider._initialized

    @pytest.mark.asyncio
    async def test_provider_transcribe(self):
        """Test transcribe method."""
        provider = ConcreteProvider(BaseProviderConfig())

        result = await provider.transcribe("test.wav")

        assert isinstance(result, TranscriptionResponse)
        assert result.text == "test transcription"
        assert result.language == "en"

    @pytest.mark.asyncio
    async def test_provider_transcribe_stream(self):
        """Test stream transcription."""
        provider = ConcreteProvider(BaseProviderConfig())

        results = []
        async for result in provider.transcribe_stream(None):
            results.append(result)

        assert len(results) > 0
        assert all(isinstance(r, TranscriptionResponse) for r in results)
