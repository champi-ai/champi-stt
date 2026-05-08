"""Shared fixtures for benchmarks."""

from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture(scope="session")
def sample_audio_1s() -> np.ndarray:
    """One second of 440 Hz sine at 16 kHz, float32."""
    t = np.linspace(0, 1.0, 16000, endpoint=False)
    return (np.sin(2 * np.pi * 440 * t)).astype(np.float32)


@pytest.fixture(scope="session")
def sample_audio_5s() -> np.ndarray:
    """Five seconds of 440 Hz sine at 16 kHz, float32."""
    t = np.linspace(0, 5.0, 80000, endpoint=False)
    return (np.sin(2 * np.pi * 440 * t)).astype(np.float32)
