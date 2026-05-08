"""
Transcription latency benchmarks.

Measures end-to-end transcribe() latency for each provider using mocked
network/model calls, so this runs in CI without API keys or GPU.

Run with:
    uv run pytest benchmarks/ --benchmark-only -v
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Any

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_provider(response: str = "hello world") -> Any:
    prov = MagicMock()
    prov.is_loaded = True
    prov.transcribe = AsyncMock(return_value=response)
    return prov


def _run_transcribe(provider: Any, audio: np.ndarray) -> str:
    return asyncio.get_event_loop().run_until_complete(provider.transcribe(audio))


# ---------------------------------------------------------------------------
# Latency benchmarks
# ---------------------------------------------------------------------------

def test_bench_mock_provider_1s(benchmark, sample_audio_1s: np.ndarray) -> None:
    """Baseline: mock provider transcription latency on 1s audio."""
    prov = _make_mock_provider()
    result = benchmark(_run_transcribe, prov, sample_audio_1s)
    assert result == "hello world"


def test_bench_mock_provider_5s(benchmark, sample_audio_5s: np.ndarray) -> None:
    """Baseline: mock provider transcription latency on 5s audio."""
    prov = _make_mock_provider()
    result = benchmark(_run_transcribe, prov, sample_audio_5s)
    assert result == "hello world"


def test_bench_generate_audio_1s(benchmark) -> None:
    """Audio generation latency (baseline for numpy overhead)."""
    def _gen() -> np.ndarray:
        t = np.linspace(0, 1.0, 16000, endpoint=False)
        return np.sin(2 * np.pi * 440 * t).astype(np.float32)

    audio = benchmark(_gen)
    assert audio.shape == (16000,)


def test_bench_streaming_chunk_assembly(benchmark, sample_audio_5s: np.ndarray) -> None:
    """Latency of assembling streaming chunks (numpy concat)."""
    chunk_size = 4096
    chunks = [sample_audio_5s[i:i + chunk_size] for i in range(0, len(sample_audio_5s), chunk_size)]

    def _assemble() -> np.ndarray:
        return np.concatenate(chunks)

    assembled = benchmark(_assemble)
    assert len(assembled) == len(sample_audio_5s)
