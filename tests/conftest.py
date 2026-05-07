"""Pytest configuration and shared fixtures."""

import asyncio
import tempfile
from collections.abc import Generator
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_audio_data() -> np.ndarray:
    """Generate sample audio data for testing."""
    # Generate 1 second of silence at 16kHz
    sample_rate = 16000
    duration = 1.0
    samples = int(sample_rate * duration)
    return np.zeros(samples, dtype=np.int16)


@pytest.fixture
def sample_audio_file(sample_audio_data: np.ndarray) -> Generator[Path, None, None]:
    """Create a temporary audio file for testing."""
    import soundfile as sf

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        sf.write(tmp_path, sample_audio_data, 16000)
        yield tmp_path
        tmp_path.unlink()


@pytest.fixture
def temp_config_file() -> Generator[Path, None, None]:
    """Create a temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(
            """
provider:
  name: whisperlive
  model: base

assistant:
  wake_word:
    engine: porcupine
    access_key: test_key
    keywords:
      - computer
"""
        )
        tmp.flush()
        yield tmp_path
        tmp_path.unlink()


@pytest.fixture
def mock_transcription_result() -> dict:
    """Mock transcription result."""
    return {
        "text": "hello world",
        "language": "en",
        "segments": [
            {
                "text": "hello world",
                "start": 0.0,
                "end": 1.0,
                "confidence": 0.95,
            }
        ],
    }
