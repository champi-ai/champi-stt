"""Tests for base provider abstract class."""

from unittest.mock import AsyncMock, patch
from typing import Any

import numpy as np
import pytest

from champi_stt.core.base_config import BaseSTTConfig
from champi_stt.core.base_provider import BaseSTTProvider
from champi_stt.core.response import TranscriptionResponse


# Concrete config for testing
from dataclasses import dataclass

@dataclass
class _TestConfig(BaseSTTConfig):
    @classmethod
    def from_env(cls) -> "_TestConfig":
        return cls()


class _ConcreteProvider(BaseSTTProvider):
    def __init__(self, config: BaseSTTConfig) -> None:
        super().__init__(config)
        self.name = "TestProvider"

    async def initialize(self) -> None:
        self._initialized = True

    async def transcribe(self, audio_data: bytes | np.ndarray | str, **kwargs: Any) -> TranscriptionResponse:  # type: ignore[override]
        return TranscriptionResponse(text="test")

    async def shutdown(self) -> None:
        self._initialized = False

    @property
    def is_loaded(self) -> bool:
        return self._initialized


@pytest.fixture
def provider():
    return _ConcreteProvider(_TestConfig())


class TestBaseSTTProvider:
    def test_initial_state(self, provider):
        assert not provider._initialized
        assert not provider.is_loaded

    @pytest.mark.asyncio
    async def test_initialize(self, provider):
        await provider.initialize()
        assert provider.is_loaded

    @pytest.mark.asyncio
    async def test_shutdown(self, provider):
        await provider.initialize()
        await provider.shutdown()
        assert not provider.is_loaded

    @pytest.mark.asyncio
    async def test_translate_calls_transcribe(self, provider):
        await provider.initialize()
        result = await provider.translate(b"audio")
        assert isinstance(result, TranscriptionResponse)

    @pytest.mark.asyncio
    async def test_detect_language_default(self, provider):
        lang, prob, all_langs = await provider.detect_language(b"audio")
        assert lang == "en"
        assert prob == 1.0
        assert all_langs == []

    @pytest.mark.asyncio
    async def test_get_model_info_not_initialized(self, provider):
        info = await provider.get_model_info()
        assert info["status"] == "not_initialized"
        assert "provider" in info

    @pytest.mark.asyncio
    async def test_get_model_info_initialized(self, provider):
        await provider.initialize()
        info = await provider.get_model_info()
        assert info["status"] == "loaded"

    @pytest.mark.asyncio
    async def test_save_transcription_disabled(self, provider):
        result = await provider.save_transcription("hello")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_transcription_enabled(self, tmp_path, provider):
        provider.config.save_transcriptions = True
        provider.config.transcriptions_dir = str(tmp_path)
        result = await provider.save_transcription("hello world")
        assert result is not None
        assert "hello world" in open(result).read()
