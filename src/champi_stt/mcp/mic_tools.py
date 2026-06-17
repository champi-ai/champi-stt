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

_DEFAULT_PROVIDER = "whisperlive"


def _resolve_device(device_index: int | None) -> int | None:
    """Return the audio input device index to use.

    Resolves in priority order: explicit argument → ``CHAMPI_INPUT_DEVICE_INDEX``
    environment variable → ``None`` (sounddevice system default).

    Args:
        device_index: Caller-supplied device index, or ``None`` to use fallbacks.

    Returns:
        Integer device index, or ``None`` to let sounddevice pick the default.
    """
    if device_index is not None:
        return device_index
    env = os.environ.get("CHAMPI_INPUT_DEVICE_INDEX")
    return int(env) if env else None


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


def list_audio_devices() -> list[dict[str, object]]:
    """Return available audio input devices.

    Returns:
        List of dicts with keys ``index``, ``name``, ``max_input_channels``,
        ``default_samplerate``, and ``is_default`` for each input-capable device.
    """
    _check_sounddevice()
    import sounddevice as sd

    devices = sd.query_devices()
    result = []
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            result.append(
                {
                    "index": i,
                    "name": dev["name"],
                    "max_input_channels": dev["max_input_channels"],
                    "default_samplerate": dev["default_samplerate"],
                    "is_default": i == sd.default.device[0],
                }
            )
    return result


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
        provider_name: Provider key (e.g. ``"whisperlive"``), or None to fall
            back to the ``CHAMPI_STT_PROVIDER`` env var, then ``"whisperlive"``.

    Returns:
        Transcription text string.
    """
    effective_provider = (
        provider_name or os.environ.get("CHAMPI_STT_PROVIDER") or _DEFAULT_PROVIDER
    )
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
    device_index: int | None = None,
) -> str:
    """Record audio from a microphone and return the transcription.

    Captures ``duration_seconds`` of audio at 16 kHz mono int16 via
    sounddevice, then passes the raw array to the provider transcription
    pipeline.

    Args:
        duration_seconds: Recording length in seconds.
        language: BCP-47 language code hint, or None for auto-detect.
        provider: Provider key (e.g. ``"whisperlive"``), or None to use
            the default.
        device_index: Input device index to record from. Falls back to
            ``CHAMPI_INPUT_DEVICE_INDEX`` env var, then the system default.

    Returns:
        Transcription text on success, or ``"error: <ExcType>: <message>"``
        on failure.
    """
    try:
        _check_sounddevice()
        import sounddevice as sd

        loop = asyncio.get_event_loop()
        num_frames = int(duration_seconds * 16000)
        device = _resolve_device(device_index)

        audio = await loop.run_in_executor(
            None,
            lambda: sd.rec(
                num_frames, samplerate=16000, channels=1, dtype="int16", device=device
            ),
        )
        await loop.run_in_executor(None, sd.wait)

        return await _audio_to_text(audio.squeeze(), 16000, language, provider)
    except Exception as e:
        return f"error: {type(e).__name__}: {e}"


async def listen_until_silence(
    max_duration_seconds: float = 30.0,
    silence_threshold_ms: int = 800,
    language: str | None = None,
    provider: str | None = None,
    device_index: int | None = None,
) -> str:
    """Record from a microphone until silence is detected, then return the transcription.

    Uses WebRTC VAD (aggressiveness level 2) to detect speech/silence boundaries.
    Recording stops when consecutive silence exceeds ``silence_threshold_ms`` or
    the total duration reaches ``max_duration_seconds``.

    Falls back to :func:`listen_once` if ``webrtcvad`` is not installed.

    Args:
        max_duration_seconds: Hard upper limit on recording length in seconds.
        silence_threshold_ms: Consecutive silence in milliseconds that triggers stop.
        language: BCP-47 language code hint, or None for auto-detect.
        provider: Provider key (e.g. ``"whisperlive"``), or None to use the default.
        device_index: Input device index to record from. Falls back to
            ``CHAMPI_INPUT_DEVICE_INDEX`` env var, then the system default.

    Returns:
        Transcription text on success, or ``"error: <ExcType>: <message>"`` on failure.
    """
    try:
        _check_sounddevice()

        try:
            import webrtcvad  # noqa: F401
        except ImportError:
            return await listen_once(
                max_duration_seconds, language, provider, device_index
            )

        import sounddevice as sd

        device = _resolve_device(device_index)

        def _record_with_vad() -> np.ndarray:
            import webrtcvad as _webrtcvad

            vad = _webrtcvad.Vad(2)
            frame_samples = int(16000 * 0.03)  # 480
            frames: list[np.ndarray] = []
            silent_ms = 0
            total_ms = 0
            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="int16",
                blocksize=frame_samples,
                device=device,
            ) as stream:
                while total_ms < max_duration_seconds * 1000:
                    chunk, _ = stream.read(frame_samples)
                    frame = chunk.squeeze()
                    frames.append(frame)
                    total_ms += 30
                    is_speech = vad.is_speech(frame.tobytes(), 16000)
                    if is_speech:
                        silent_ms = 0
                    else:
                        silent_ms += 30
                        if silent_ms >= silence_threshold_ms:
                            break
            return (
                np.concatenate(frames)
                if frames
                else np.zeros(frame_samples, dtype=np.int16)
            )

        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(None, _record_with_vad)
        return await _audio_to_text(audio, 16000, language, provider)
    except Exception as e:
        return f"error: {type(e).__name__}: {e}"
