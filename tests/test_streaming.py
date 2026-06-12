"""Tests for streaming transcription pipeline."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest

from champi_stt.core.base_config import BaseSTTConfig
from champi_stt.core.base_provider import BaseSTTProvider
from champi_stt.core.base_transcriber import BaseTranscriber
from champi_stt.core.response import TranscriptionChunk
from champi_stt.core.streaming import StreamingTranscriptionConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_source(
    *chunks: bytes | np.ndarray,
) -> AsyncIterator[bytes | np.ndarray]:
    for c in chunks:
        yield c


class _ConcreteProvider(BaseSTTProvider):
    def __init__(self) -> None:
        cfg = MagicMock(spec=BaseSTTConfig)
        cfg.save_transcriptions = False
        super().__init__(cfg)
        self._initialized = True

    async def initialize(self) -> None:
        self._initialized = True

    async def transcribe(
        self, audio_data: Any, language: Any = None, **kwargs: Any
    ) -> str:
        return "hello world"

    async def shutdown(self) -> None:
        pass

    @property
    def is_loaded(self) -> bool:
        return self._initialized


class _ConcreteTranscriber(BaseTranscriber):
    async def initialize(self) -> None:
        pass

    async def transcribe_audio(self, audio: Any, **kwargs: Any) -> dict[str, Any]:
        return {"text": "streamed text"}

    async def shutdown(self) -> None:
        pass

    @property
    def is_loaded(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# StreamingTranscriptionConfig
# ---------------------------------------------------------------------------


class TestStreamingTranscriptionConfig:
    def test_defaults(self) -> None:
        cfg = StreamingTranscriptionConfig()
        assert cfg.chunk_size == 4096
        assert cfg.overlap_frames == 512
        assert cfg.vad_aggressiveness == 2
        assert cfg.language is None
        assert cfg.sample_rate == 16000

    def test_custom_values(self) -> None:
        cfg = StreamingTranscriptionConfig(chunk_size=2048, language="es")
        assert cfg.chunk_size == 2048
        assert cfg.language == "es"

    def test_invalid_chunk_size(self) -> None:
        with pytest.raises(ValueError, match="chunk_size"):
            StreamingTranscriptionConfig(chunk_size=0)

    def test_invalid_overlap(self) -> None:
        with pytest.raises(ValueError, match="overlap_frames"):
            StreamingTranscriptionConfig(overlap_frames=-1)

    def test_invalid_vad(self) -> None:
        with pytest.raises(ValueError, match="vad_aggressiveness"):
            StreamingTranscriptionConfig(vad_aggressiveness=4)

    def test_invalid_sample_rate(self) -> None:
        with pytest.raises(ValueError, match="sample_rate"):
            StreamingTranscriptionConfig(sample_rate=0)


# ---------------------------------------------------------------------------
# TranscriptionChunk
# ---------------------------------------------------------------------------


class TestTranscriptionChunk:
    def test_defaults(self) -> None:
        chunk = TranscriptionChunk()
        assert chunk.text == ""
        assert chunk.is_final is False
        assert chunk.confidence == 0.0

    def test_final_chunk(self) -> None:
        chunk = TranscriptionChunk(text="done", is_final=True, language="en")
        assert chunk.is_final is True
        assert chunk.language == "en"


# ---------------------------------------------------------------------------
# BaseSTTProvider.stream_transcribe (default implementation)
# ---------------------------------------------------------------------------


class TestBaseProviderStreamTranscribe:
    @pytest.mark.asyncio
    async def test_yields_single_final_chunk_from_bytes(self) -> None:
        provider = _ConcreteProvider()
        audio_bytes = (np.zeros(1024, dtype=np.int16) * 0).tobytes()
        source = _make_source(audio_bytes)
        results = [c async for c in await _collect(provider, source)]
        assert len(results) == 1
        assert results[0].is_final is True
        assert results[0].text == "hello world"

    @pytest.mark.asyncio
    async def test_yields_single_final_chunk_from_ndarray(self) -> None:
        provider = _ConcreteProvider()
        arr = np.zeros(512, dtype=np.float32)
        source = _make_source(arr)
        results = [c async for c in await _collect(provider, source)]
        assert len(results) == 1
        assert results[0].is_final is True

    @pytest.mark.asyncio
    async def test_empty_source_yields_nothing(self) -> None:
        provider = _ConcreteProvider()

        async def empty() -> AsyncIterator[bytes]:
            return
            yield  # make it an async generator

        results = [c async for c in await _collect(provider, empty())]
        assert results == []

    @pytest.mark.asyncio
    async def test_multiple_chunks_concatenated(self) -> None:
        provider = _ConcreteProvider()
        chunk1 = np.zeros(256, dtype=np.float32)
        chunk2 = np.zeros(256, dtype=np.float32)
        source = _make_source(chunk1, chunk2)
        results = [c async for c in await _collect(provider, source)]
        assert len(results) == 1


# ---------------------------------------------------------------------------
# BaseTranscriber.stream_transcribe (default implementation)
# ---------------------------------------------------------------------------


class TestBaseTranscriberStreamTranscribe:
    @pytest.mark.asyncio
    async def test_yields_chunk_with_text(self) -> None:
        transcriber = _ConcreteTranscriber()
        arr = np.zeros(512, dtype=np.float32)
        source = _make_source(arr)
        results = [c async for c in await _collect_t(transcriber, source)]
        assert len(results) == 1
        assert results[0].text == "streamed text"
        assert results[0].is_final is True

    @pytest.mark.asyncio
    async def test_bytes_chunk_converted(self) -> None:
        transcriber = _ConcreteTranscriber()
        raw = np.zeros(512, dtype=np.int16).tobytes()
        source = _make_source(raw)
        results = [c async for c in await _collect_t(transcriber, source)]
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Helpers to drive async generators
# ---------------------------------------------------------------------------


async def _collect(
    provider: BaseSTTProvider,
    source: AsyncIterator[bytes | np.ndarray],
) -> AsyncIterator[TranscriptionChunk]:
    return provider.stream_transcribe(source)


async def _collect_t(
    transcriber: BaseTranscriber,
    source: AsyncIterator[bytes | np.ndarray],
) -> AsyncIterator[TranscriptionChunk]:
    return transcriber.stream_transcribe(source)
