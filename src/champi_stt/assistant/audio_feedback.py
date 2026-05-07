"""Audio feedback system for assistant notifications.

Provides simple chime sounds for wake word detection and recording states.
"""

import asyncio
import logging
from typing import Literal

import numpy as np

logger = logging.getLogger(__name__)


def generate_chime(
    frequencies: list[float], duration: float = 0.1, sample_rate: int = 16000
) -> np.ndarray:
    """Generate a chime sound with given frequencies.

    Args:
        frequencies: List of frequencies to play in sequence
        duration: Duration of each tone in seconds
        sample_rate: Sample rate for audio generation

    Returns:
        Numpy array of audio samples
    """
    samples_per_tone = int(sample_rate * duration)
    fade_samples = int(sample_rate * 0.01)  # 10ms fade

    all_samples = []
    for freq in frequencies:
        # Generate sine wave
        t = np.linspace(0, duration, samples_per_tone, endpoint=False)
        tone = np.sin(2 * np.pi * freq * t)

        # Apply fade in/out
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)

        tone[:fade_samples] *= fade_in
        tone[-fade_samples:] *= fade_out

        all_samples.append(tone)

    # Concatenate all tones
    return np.concatenate(all_samples).astype(np.float32)


async def play_chime_start(sample_rate: int = 16000) -> bool:
    """Play the recording start chime (ascending tones).

    Returns:
        True if chime played successfully, False otherwise
    """
    try:
        import sounddevice as sd

        # Get default output device sample rate
        try:
            default_device = sd.query_devices(kind="output")
            device_rate = int(default_device["default_samplerate"])
        except Exception:
            device_rate = 44100  # Fallback to common rate

        chime = generate_chime([800, 1000], duration=0.1, sample_rate=device_rate)
        sd.play(chime, device_rate, latency="high")  # Allow shared device access
        sd.wait()
        return True
    except Exception as e:
        logger.debug(f"Could not play start chime: {e}")
        return False


async def play_chime_end(sample_rate: int = 16000) -> bool:
    """Play the recording end chime (descending tones).

    Returns:
        True if chime played successfully, False otherwise
    """
    try:
        import sounddevice as sd

        # Get default output device sample rate
        try:
            default_device = sd.query_devices(kind="output")
            device_rate = int(default_device["default_samplerate"])
        except Exception:
            device_rate = 44100  # Fallback to common rate

        chime = generate_chime([1000, 800], duration=0.1, sample_rate=device_rate)
        sd.play(chime, device_rate, latency="high")  # Allow shared device access
        sd.wait()
        return True
    except Exception as e:
        logger.debug(f"Could not play end chime: {e}")
        return False


async def play_chime_wake(sample_rate: int = 16000) -> bool:
    """Play the wake word detected chime (high ascending tones).

    Returns:
        True if chime played successfully, False otherwise
    """
    try:
        import sounddevice as sd

        # Get default output device sample rate
        try:
            default_device = sd.query_devices(kind="output")
            device_rate = int(default_device["default_samplerate"])
        except Exception:
            device_rate = 44100  # Fallback to common rate

        chime = generate_chime(
            [1000, 1200, 1400], duration=0.08, sample_rate=device_rate
        )
        sd.play(chime, device_rate, latency="high")  # Allow shared device access
        sd.wait()
        return True
    except Exception as e:
        logger.debug(f"Could not play wake chime: {e}")
        return False


async def play_audio_feedback(
    feedback_type: Literal["listening", "finished", "wake"], enabled: bool | None = None
) -> None:
    """Play audio feedback chime.

    Args:
        feedback_type: Type of feedback ("listening", "finished", or "wake")
        enabled: Whether feedback is enabled (None means always play)
    """
    if enabled is False:
        return

    try:
        if feedback_type == "listening":
            await play_chime_start()
        elif feedback_type == "finished":
            await play_chime_end()
        elif feedback_type == "wake":
            await play_chime_wake()
        else:
            logger.warning(f"Unknown feedback type: {feedback_type}")
    except Exception as e:
        logger.debug(f"Audio feedback failed: {e}")


# Run chime test if module is executed directly
if __name__ == "__main__":
    import asyncio

    async def test_chimes():
        """Test all chime sounds."""
        logger.info("Testing wake chime...")
        await play_audio_feedback("wake")
        await asyncio.sleep(0.5)

        logger.info("Testing listening chime...")
        await play_audio_feedback("listening")
        await asyncio.sleep(0.5)

        logger.info("Testing finished chime...")
        await play_audio_feedback("finished")

    asyncio.run(test_chimes())
