"""
Generic audio preprocessing utilities for all STT providers.

Provides reusable audio preprocessing functions:
- Normalization
- Resampling
- Format conversion
- Dtype conversion
"""

import asyncio
import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


async def normalize_audio(audio_data: np.ndarray) -> np.ndarray:
    """
    Normalize audio to float32 in range [-1.0, 1.0].

    Args:
        audio_data: Audio data (any dtype)

    Returns:
        Normalized audio as float32
    """
    # Convert to float32 if needed
    if audio_data.dtype != np.float32:
        if audio_data.dtype == np.int16:
            # int16 range: -32768 to 32767
            audio_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype == np.int32:
            # int32 range: -2147483648 to 2147483647
            audio_data = audio_data.astype(np.float32) / 2147483648.0
        else:
            audio_data = audio_data.astype(np.float32)

    # Normalize to [-1.0, 1.0] if needed
    max_val = np.max(np.abs(audio_data))
    if max_val > 1.0:
        audio_data = audio_data / max_val

    return audio_data


async def resample_audio(
    audio_data: np.ndarray,
    orig_sample_rate: int,
    target_sample_rate: int
) -> np.ndarray:
    """
    Resample audio to target sample rate.

    Args:
        audio_data: Audio data as numpy array
        orig_sample_rate: Original sample rate
        target_sample_rate: Target sample rate

    Returns:
        Resampled audio data
    """
    if orig_sample_rate == target_sample_rate:
        return audio_data

    from scipy import signal as scipy_signal

    logger.debug(f"Resampling audio: {orig_sample_rate}Hz → {target_sample_rate}Hz")

    # Calculate target length
    target_length = int(len(audio_data) * target_sample_rate / orig_sample_rate)

    # Resample in executor to avoid blocking
    loop = asyncio.get_running_loop()
    resampled = await loop.run_in_executor(
        None,
        lambda: scipy_signal.resample(audio_data, target_length)
    )

    return resampled.astype(audio_data.dtype)


async def convert_to_float32(audio_data: np.ndarray) -> np.ndarray:
    """
    Convert audio to float32 format.

    Args:
        audio_data: Audio data (any dtype)

    Returns:
        Audio as float32
    """
    if audio_data.dtype == np.float32:
        return audio_data

    return await normalize_audio(audio_data)


async def convert_to_int16(audio_data: np.ndarray) -> np.ndarray:
    """
    Convert audio to int16 format.

    Args:
        audio_data: Audio data (any dtype)

    Returns:
        Audio as int16
    """
    if audio_data.dtype == np.int16:
        return audio_data

    # First normalize to float32 in [-1.0, 1.0]
    normalized = await normalize_audio(audio_data)

    # Convert to int16
    return (normalized * 32767).astype(np.int16)


async def prepare_audio_for_stt(
    audio_data: np.ndarray,
    current_sample_rate: int,
    target_sample_rate: int = 16000,
    target_dtype: str = "float32"
) -> np.ndarray:
    """
    Prepare audio for STT processing.

    Standard preprocessing pipeline:
    1. Convert to target dtype
    2. Normalize
    3. Resample to target sample rate

    Args:
        audio_data: Input audio data
        current_sample_rate: Current sample rate
        target_sample_rate: Target sample rate (default: 16000 for Whisper)
        target_dtype: Target dtype ("float32" or "int16")

    Returns:
        Preprocessed audio data
    """
    # Step 1: Convert to target dtype and normalize
    if target_dtype == "float32":
        audio_data = await convert_to_float32(audio_data)
    elif target_dtype == "int16":
        audio_data = await convert_to_int16(audio_data)
    else:
        raise ValueError(f"Unsupported target_dtype: {target_dtype}")

    # Step 2: Resample if needed
    if current_sample_rate != target_sample_rate:
        audio_data = await resample_audio(
            audio_data,
            current_sample_rate,
            target_sample_rate
        )

    return audio_data


def get_audio_duration(audio_data: np.ndarray, sample_rate: int) -> float:
    """
    Calculate duration of audio in seconds.

    Args:
        audio_data: Audio data as numpy array
        sample_rate: Sample rate of the audio

    Returns:
        Duration in seconds
    """
    return len(audio_data) / sample_rate


def get_audio_stats(audio_data: np.ndarray) -> dict[str, Any]:
    """
    Get statistics about audio data.

    Args:
        audio_data: Audio data as numpy array

    Returns:
        Dictionary with audio statistics
    """
    return {
        "shape": audio_data.shape,
        "dtype": str(audio_data.dtype),
        "min": float(np.min(audio_data)),
        "max": float(np.max(audio_data)),
        "mean": float(np.mean(audio_data)),
        "rms": float(np.sqrt(np.mean(audio_data.astype(float) ** 2))),
        "samples": len(audio_data),
    }
