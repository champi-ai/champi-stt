"""Audio feedback system for assistant notifications.

Provides chime sounds for wake word detection and recording states,
with configurable themes and volume control.
"""

from __future__ import annotations

import logging
import threading
from enum import StrEnum
from typing import Literal

import numpy as np

logger = logging.getLogger(__name__)


class FeedbackTheme(StrEnum):
    """Sound theme for audio feedback."""

    DEFAULT = "default"
    MINIMAL = "minimal"
    SILENT = "silent"


_THEME_FREQS: dict[FeedbackTheme, dict[str, list[float]]] = {
    FeedbackTheme.DEFAULT: {
        "wake": [1000.0, 1200.0, 1400.0],
        "listening": [800.0, 1000.0],
        "finished": [1000.0, 800.0],
    },
    FeedbackTheme.MINIMAL: {
        "wake": [1200.0],
        "listening": [900.0],
        "finished": [700.0],
    },
    FeedbackTheme.SILENT: {
        "wake": [],
        "listening": [],
        "finished": [],
    },
}

_THEME_DURATIONS: dict[FeedbackTheme, float] = {
    FeedbackTheme.DEFAULT: 0.1,
    FeedbackTheme.MINIMAL: 0.06,
    FeedbackTheme.SILENT: 0.0,
}


def generate_chime(
    frequencies: list[float],
    duration: float = 0.1,
    sample_rate: int = 16000,
    volume: float = 1.0,
) -> np.ndarray:
    """Generate a chime sound with given frequencies.

    Args:
        frequencies: List of frequencies to play in sequence
        duration: Duration of each tone in seconds
        sample_rate: Sample rate for audio generation
        volume: Amplitude multiplier in [0.0, 1.0]

    Returns:
        Numpy array of audio samples (float32)
    """
    if not frequencies or duration <= 0:
        return np.zeros(0, dtype=np.float32)

    volume = float(np.clip(volume, 0.0, 1.0))
    samples_per_tone = int(sample_rate * duration)
    fade_samples = max(1, int(sample_rate * 0.01))  # 10 ms fade

    all_samples: list[np.ndarray] = []
    for freq in frequencies:
        t = np.linspace(0, duration, samples_per_tone, endpoint=False)
        tone: np.ndarray = np.sin(2 * np.pi * freq * t)

        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        tone[:fade_samples] *= fade_in
        tone[-fade_samples:] *= fade_out

        all_samples.append(tone * volume)

    result: np.ndarray = np.concatenate(all_samples).astype(np.float32)
    return result


def _play_nonblocking(audio: np.ndarray, sample_rate: int) -> None:
    """Play audio on a background thread so the caller is never blocked."""

    def _run() -> None:
        try:
            import sounddevice as sd  # type: ignore[import-untyped]

            sd.play(audio, sample_rate, latency="high")
            sd.wait()
        except Exception as exc:
            logger.debug(f"Audio playback failed: {exc}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def _device_sample_rate() -> int:
    try:
        import sounddevice as sd  # type: ignore[import-untyped]

        device = sd.query_devices(kind="output")
        return int(device["default_samplerate"])
    except Exception:
        return 44100


async def play_chime_start(
    theme: FeedbackTheme = FeedbackTheme.DEFAULT,
    volume: float = 1.0,
) -> bool:
    """Play the recording start chime.

    Returns:
        True if chime was dispatched, False on error.
    """
    if theme is FeedbackTheme.SILENT:
        return True
    try:
        rate = _device_sample_rate()
        freqs = _THEME_FREQS[theme]["listening"]
        dur = _THEME_DURATIONS[theme]
        audio = generate_chime(freqs, duration=dur, sample_rate=rate, volume=volume)
        _play_nonblocking(audio, rate)
        return True
    except Exception as e:
        logger.debug(f"Could not play start chime: {e}")
        return False


async def play_chime_end(
    theme: FeedbackTheme = FeedbackTheme.DEFAULT,
    volume: float = 1.0,
) -> bool:
    """Play the recording end chime.

    Returns:
        True if chime was dispatched, False on error.
    """
    if theme is FeedbackTheme.SILENT:
        return True
    try:
        rate = _device_sample_rate()
        freqs = _THEME_FREQS[theme]["finished"]
        dur = _THEME_DURATIONS[theme]
        audio = generate_chime(freqs, duration=dur, sample_rate=rate, volume=volume)
        _play_nonblocking(audio, rate)
        return True
    except Exception as e:
        logger.debug(f"Could not play end chime: {e}")
        return False


async def play_chime_wake(
    theme: FeedbackTheme = FeedbackTheme.DEFAULT,
    volume: float = 1.0,
) -> bool:
    """Play the wake word detected chime.

    Returns:
        True if chime was dispatched, False on error.
    """
    if theme is FeedbackTheme.SILENT:
        return True
    try:
        rate = _device_sample_rate()
        freqs = _THEME_FREQS[theme]["wake"]
        dur = _THEME_DURATIONS[theme]
        audio = generate_chime(freqs, duration=dur, sample_rate=rate, volume=volume)
        _play_nonblocking(audio, rate)
        return True
    except Exception as e:
        logger.debug(f"Could not play wake chime: {e}")
        return False


async def play_audio_feedback(
    feedback_type: Literal["listening", "finished", "wake"],
    enabled: bool | None = None,
    theme: FeedbackTheme = FeedbackTheme.DEFAULT,
    volume: float = 1.0,
) -> None:
    """Play audio feedback chime.

    Args:
        feedback_type: Type of feedback ("listening", "finished", or "wake")
        enabled: Whether feedback is enabled (None means always play)
        theme: Sound theme to use
        volume: Amplitude multiplier in [0.0, 1.0]
    """
    if enabled is False:
        return

    try:
        if feedback_type == "listening":
            await play_chime_start(theme=theme, volume=volume)
        elif feedback_type == "finished":
            await play_chime_end(theme=theme, volume=volume)
        elif feedback_type == "wake":
            await play_chime_wake(theme=theme, volume=volume)
        else:
            logger.warning(f"Unknown feedback type: {feedback_type}")
    except Exception as e:
        logger.debug(f"Audio feedback failed: {e}")


if __name__ == "__main__":
    import asyncio

    async def _test() -> None:
        for theme in FeedbackTheme:
            print(f"Theme: {theme.value}")
            await play_audio_feedback("wake", theme=theme)
            await asyncio.sleep(0.5)
            await play_audio_feedback("listening", theme=theme)
            await asyncio.sleep(0.5)
            await play_audio_feedback("finished", theme=theme)
            await asyncio.sleep(0.5)

    asyncio.run(_test())
