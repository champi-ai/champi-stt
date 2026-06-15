"""Internal audio bridge helper for MCP mic tools.

Bridges captured numpy int16 audio arrays to the existing provider
transcription pipeline. Intended for use by Phase 5 MCP mic tools.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import tempfile

import numpy as np
import soundfile as sf

from champi_stt.core.response import TranscriptionResponse
from champi_stt.factory import get_provider


def _check_sounddevice() -> None:
    """Verify that sounddevice and its PortAudio backend are available.

    Raises:
        ImportError: If sounddevice or PortAudio is not installed.
    """
    try:
        import sounddevice  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "sounddevice is required for microphone capture. "
            "Install PortAudio (e.g. 'sudo apt install portaudio19-dev' on Debian/Ubuntu "
            "or 'brew install portaudio' on macOS), then reinstall champi-stt."
        ) from exc


async def _audio_to_text(
    audio_array: np.ndarray,
    sample_rate: int,
    language: str | None,
    provider_name: str | None,
) -> str:
    """Transcribe a numpy int16 audio array using the provider pipeline.

    Writes the array to a temporary WAV file, runs transcription via the
    selected provider, cleans up the temp file, and returns the transcript.

    Args:
        audio_array: Captured audio samples as a numpy int16 array.
        sample_rate: Sample rate of the audio in Hz.
        language: BCP-47 language code hint, or None for auto-detect.
        provider_name: Provider key (e.g. ``"whisperlive"``), or None to use
            the default (``"whisperlive"``).

    Returns:
        Transcription text string.
    """
    effective_provider = provider_name or "whisperlive"
    loop = asyncio.get_event_loop()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name

    try:
        await loop.run_in_executor(
            None,
            lambda: sf.write(wav_path, audio_array, sample_rate, subtype="PCM_16"),
        )

        provider = get_provider(effective_provider)
        await provider.initialize()

        result = await loop.run_in_executor(
            None,
            lambda: asyncio.run(provider.transcribe(wav_path, language=language)),
        )

        if isinstance(result, TranscriptionResponse):
            return result.text
        if isinstance(result, dict):
            return str(result.get("text", ""))
        return str(result)

    finally:
        with contextlib.suppress(FileNotFoundError):
            os.remove(wav_path)


async def listen_once(
    duration_seconds: float = 5.0,
    language: str | None = None,
    provider: str | None = None,
) -> str:
    """Record audio from the default microphone and return the transcription.

    Captures ``duration_seconds`` of audio at 16 kHz mono int16 via
    sounddevice, then passes the raw array to the provider transcription
    pipeline.

    Args:
        duration_seconds: Recording length in seconds.
        language: BCP-47 language code hint, or None for auto-detect.
        provider: Provider key (e.g. ``"whisperlive"``), or None to use
            the default.

    Returns:
        Transcription text on success, or ``"error: <ExcType>: <message>"``
        on failure.
    """
    try:
        _check_sounddevice()
        import sounddevice as sd

        loop = asyncio.get_event_loop()
        num_frames = int(duration_seconds * 16000)

        audio = await loop.run_in_executor(
            None,
            lambda: sd.rec(num_frames, samplerate=16000, channels=1, dtype="int16"),
        )
        await loop.run_in_executor(None, sd.wait)

        return await _audio_to_text(audio.squeeze(), 16000, language, provider)
    except Exception as e:
        return f"error: {type(e).__name__}: {e}"
