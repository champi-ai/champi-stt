"""
Generic audio handling utilities for all STT providers.

This module provides reusable audio functionality:
- Audio device management
- Recording (fixed duration and VAD-based)
- Playback
- Audio data loading from various sources
"""

import asyncio
import dataclasses
import queue
from pathlib import Path
from typing import Any

import numpy as np
import sounddevice as sd
from loguru import logger

# Optional webrtcvad for silence detection
try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError:
    webrtcvad = None
    VAD_AVAILABLE = False


@dataclasses.dataclass
class AudioFormat:
    """Audio format specification."""

    sample_rate: int = 16000  # Sample rate in Hz
    channels: int = 1  # Number of audio channels
    sample_width: int = 2  # Sample width in bytes (2 = 16-bit)


@dataclasses.dataclass
class AudioDevice:
    """Audio device configuration"""
    name: str
    device_id: str
    sample_rate: int
    chunk_size: int
    input_channels: int
    output_channels: int


def list_input_devices() -> list[dict[str, Any]]:
    """
    List all available audio input devices.

    Returns:
        List of input device dictionaries with keys: index, name, channels, sample_rate
    """
    devices = sd.query_devices()
    input_devices = []

    for device in devices:
        if device["max_input_channels"] > 0:
            input_devices.append({
                "index": device["index"],
                "name": device["name"],
                "channels": device["max_input_channels"],
                "sample_rate": int(device["default_samplerate"]),
            })

    return input_devices


def get_audio_device(device_name: str) -> AudioDevice:
    """
    Find and configure audio device by name.

    Args:
        device_name: Name (or partial name) of the audio device

    Returns:
        AudioDevice configuration

    Raises:
        ValueError: If device not found
    """
    devices = sd.query_devices()

    device_raw = next(
        (d for i, d in enumerate(devices) if device_name in d["name"]), None
    )

    if device_raw is None:
        raise ValueError(f"Could not find audio device: {device_name}")

    device = AudioDevice(
        name=device_raw["name"],
        device_id=device_raw["index"],
        sample_rate=int(device_raw["default_samplerate"]),
        chunk_size=1024,
        input_channels=device_raw["max_input_channels"],
        output_channels=device_raw["max_output_channels"],
    )

    logger.debug(f"Using audio device: {device}")
    return device


async def record_audio(
    duration: float,
    device_name: str | None = None,
    sample_rate: int = 16000
) -> np.ndarray:
    """
    Record audio from microphone for fixed duration.

    Args:
        duration: Recording duration in seconds
        device_name: Audio device name (None = default device)
        sample_rate: Sample rate for recording

    Returns:
        Audio data as numpy array (int16)
    """
    logger.debug(f"Recording audio for {duration:.1f}s...")

    try:
        # Get audio device if specified
        if device_name:
            audio_device = get_audio_device(device_name)
            device_id = audio_device.device_id
            sample_rate = audio_device.sample_rate
        else:
            device_id = None  # Use default

        samples_to_record = int(duration * sample_rate)

        loop = asyncio.get_running_loop()
        recording = await loop.run_in_executor(
            None,
            lambda: sd.rec(
                frames=samples_to_record,
                samplerate=sample_rate,
                channels=1,
                dtype=np.int16,
                device=device_id,
                latency='high'  # Allow shared device access
            )
        )
        await loop.run_in_executor(None, sd.wait)

        flattened = recording.flatten()
        logger.debug(f"✓ Recorded {len(flattened)} samples ({duration:.1f}s)")

        return flattened

    except Exception as e:
        logger.error(f"Recording failed: {e}")
        return np.array([])


async def record_audio_with_vad(
    max_duration: float,
    device_name: str | None = None,
    sample_rate: int = 16000,
    disable_vad: bool = False,
    silence_threshold_ms: int = 800,
    min_recording_duration: float = 0.3,
    vad_aggressiveness: float = 2.0,
    vad_chunk_duration_ms: int = 30,
    initial_silence_grace_period: float = 3.0,
) -> np.ndarray:
    """
    Record audio with automatic silence detection using WebRTC VAD.

    Args:
        max_duration: Maximum recording duration in seconds
        device_name: Audio device name (None = default)
        sample_rate: Sample rate for recording
        disable_vad: Disable VAD and use fixed duration
        silence_threshold_ms: Silence duration before stopping (ms)
        min_recording_duration: Minimum recording duration (seconds)
        vad_aggressiveness: VAD sensitivity (0-3, higher = more aggressive)
        vad_chunk_duration_ms: VAD processing chunk size (ms)
        initial_silence_grace_period: Grace period before checking for silence (seconds)

    Returns:
        Audio data as numpy array (int16)
    """
    if not VAD_AVAILABLE or disable_vad:
        logger.debug("Using fixed duration recording (VAD disabled/unavailable)")
        return await record_audio(max_duration, device_name, sample_rate)

    logger.debug(f"Recording with VAD (max {max_duration:.1f}s)...")

    try:
        return await _record_with_vad_impl(
            max_duration=max_duration,
            device_name=device_name,
            sample_rate=sample_rate,
            silence_threshold_ms=silence_threshold_ms,
            min_recording_duration=min_recording_duration,
            vad_aggressiveness=vad_aggressiveness,
            vad_chunk_duration_ms=vad_chunk_duration_ms,
            initial_silence_grace_period=initial_silence_grace_period,
        )
    except Exception as e:
        logger.error(f"VAD recording failed: {e}, falling back to fixed duration")
        return await record_audio(max_duration, device_name, sample_rate)


async def _record_with_vad_impl(
    max_duration: float,
    device_name: str | None,
    sample_rate: int,
    silence_threshold_ms: int,
    min_recording_duration: float,
    vad_aggressiveness: float,
    vad_chunk_duration_ms: int,
    initial_silence_grace_period: float,
) -> np.ndarray:
    """Internal implementation of VAD recording"""
    from scipy import signal

    # Initialize VAD
    vad = webrtcvad.Vad(int(vad_aggressiveness))

    # VAD sample rate (16kHz for WebRTC VAD compatibility)
    vad_sample_rate = 16000
    vad_chunk_samples = int(vad_sample_rate * vad_chunk_duration_ms / 1000)

    # Recording state
    chunks = []
    silence_duration_ms = 0
    recording_duration = 0
    speech_detected = True
    stop_recording = False
    vad_buffer = []

    chunk_duration_s = vad_chunk_duration_ms / 1000

    # Setup audio queue and callback
    audio_queue = queue.Queue(maxsize=-1)

    def audio_callback(indata, frames, time, status):
        if status:
            logger.warning(f"Audio stream status: {status}")
        audio_queue.put(indata.copy())

    try:
        # Get audio device
        if device_name:
            _mic_device = get_audio_device(device_name)
            mic_sample_rate = _mic_device.sample_rate
            mic_device_id = _mic_device.device_id
            mic_channels = _mic_device.input_channels
            mic_chunk_size = _mic_device.chunk_size
        else:
            mic_sample_rate = sample_rate
            mic_device_id = None
            mic_channels = 1
            mic_chunk_size = 1024

        # Start audio stream with shared access
        mic_stream = sd.InputStream(
            samplerate=mic_sample_rate,
            channels=mic_channels,
            dtype=np.int16,
            callback=audio_callback,
            blocksize=mic_chunk_size,
            device=mic_device_id,
            latency='high',  # Allow shared device access
        )

        with mic_stream:
            logger.debug("Audio stream started")
            while recording_duration < max_duration and not stop_recording:
                try:
                    chunk = await asyncio.get_running_loop().run_in_executor(
                        None, lambda: audio_queue.get(timeout=0.1)
                    )
                    chunk_flat = chunk.flatten()
                    chunks.append(chunk_flat)

                    # Add to VAD buffer
                    vad_buffer.extend(chunk_flat)

                    # Calculate buffer target size (500ms for better VAD performance)
                    vad_buffer_target_samples = int(mic_sample_rate * 0.5)

                    # Process VAD when buffer is full
                    if len(vad_buffer) < vad_buffer_target_samples:
                        recording_duration += chunk_duration_s
                        continue

                    # Take buffered audio for VAD
                    buffered_audio = np.array(vad_buffer[:vad_buffer_target_samples])
                    vad_buffer = vad_buffer[vad_buffer_target_samples:]

                    # Resample to 16kHz for VAD if needed
                    if mic_sample_rate != vad_sample_rate:
                        target_length = int(len(buffered_audio) * vad_sample_rate / mic_sample_rate)
                        buffered_float = buffered_audio.astype(np.float32)
                        resampled_float = signal.resample(buffered_float, target_length)
                        resampled_chunk = resampled_float.astype(np.int16)

                        # Ensure exact VAD chunk size
                        if len(resampled_chunk) >= vad_chunk_samples:
                            vad_chunk = resampled_chunk[:vad_chunk_samples]
                        else:
                            vad_chunk = np.zeros(vad_chunk_samples, dtype=np.int16)
                            vad_chunk[:len(resampled_chunk)] = resampled_chunk
                    else:
                        if len(chunk_flat) >= vad_chunk_samples:
                            vad_chunk = chunk_flat[:vad_chunk_samples]
                        else:
                            vad_chunk = np.zeros(vad_chunk_samples, dtype=np.int16)
                            vad_chunk[:len(chunk_flat)] = chunk_flat

                    # VAD processing
                    chunk_bytes = vad_chunk.tobytes()
                    try:
                        is_speech = vad.is_speech(chunk_bytes, vad_sample_rate)
                    except Exception as vad_e:
                        logger.warning(f"VAD error: {vad_e}, treating as speech")
                        is_speech = True

                    if is_speech:
                        speech_detected = True
                        silence_duration_ms = 0
                    else:
                        silence_duration_ms += vad_chunk_duration_ms

                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error processing audio chunk: {e}")
                    break

        # Concatenate all chunks
        if chunks:
            full_recording = np.concatenate(chunks)
            logger.debug(f"✓ Recorded {len(full_recording)} samples ({recording_duration:.1f}s)")
            return full_recording
        else:
            logger.warning("No audio chunks recorded")
            return np.array([])

    except Exception as e:
        logger.error(f"VAD recording error: {e}")
        raise


async def play_audio(
    audio_data: np.ndarray,
    sample_rate: int = 44100
) -> None:
    """
    Play audio data for verification.

    Args:
        audio_data: Audio data as numpy array
        sample_rate: Sample rate of the audio
    """
    logger.debug("Playing audio...")

    # Normalize if needed
    if np.max(np.abs(audio_data)) > 1.0:
        audio_data = audio_data / np.max(np.abs(audio_data))

    # Play audio
    loop = asyncio.get_running_loop()

    try:
        # Try PulseAudio device first
        await loop.run_in_executor(
            None,
            lambda: (sd.play(audio_data, sample_rate, device="pulse"), sd.wait())
        )
    except Exception as pulse_error:
        logger.debug(f"PulseAudio failed: {pulse_error}, trying default device")
        try:
            # Fallback to default device
            await loop.run_in_executor(
                None,
                lambda: (sd.play(audio_data, sample_rate), sd.wait())
            )
        except Exception as default_error:
            logger.error(f"Audio playback failed: {default_error}")
            raise

    logger.debug("Audio playback completed")


async def load_audio_from_file(
    file_path: str | Path,
    sample_rate: int = 16000
) -> np.ndarray:
    """
    Load audio from file.

    Args:
        file_path: Path to audio file
        sample_rate: Target sample rate

    Returns:
        Audio data as numpy array (float32, normalized)
    """
    import librosa

    loop = asyncio.get_running_loop()
    audio_data, _ = await loop.run_in_executor(
        None, lambda: librosa.load(str(file_path), sr=sample_rate, mono=True)
    )

    logger.debug(f"Loaded audio from {file_path}: shape={audio_data.shape}")
    return audio_data


class AudioCapture:
    """Simple audio capture class for recording audio from microphone."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device_name: str | None = None
    ):
        """
        Initialize audio capture.

        Args:
            sample_rate: Sample rate for recording
            channels: Number of audio channels
            device_name: Name of audio input device (None = default)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_name = device_name
        self._chunks: list[np.ndarray] = []
        self._is_recording = False

    async def start(self) -> None:
        """Start audio capture."""
        self._chunks = []
        self._is_recording = True
        logger.debug("Audio capture started")

    async def record(self, duration: float) -> np.ndarray:
        """
        Record audio for a specified duration.

        Args:
            duration: Recording duration in seconds

        Returns:
            Audio data as numpy array
        """
        return await record_audio(duration, self.device_name, self.sample_rate)

    async def record_with_vad(
        self,
        max_duration: float,
        **vad_kwargs
    ) -> np.ndarray:
        """
        Record audio with VAD-based automatic stopping.

        Args:
            max_duration: Maximum recording duration
            **vad_kwargs: Additional VAD parameters

        Returns:
            Audio data as numpy array
        """
        return await record_audio_with_vad(
            max_duration,
            self.device_name,
            self.sample_rate,
            **vad_kwargs
        )

    async def stop(self) -> None:
        """Stop audio capture."""
        self._is_recording = False
        logger.debug("Audio capture stopped")

    def get_recording(self) -> np.ndarray:
        """
        Get the captured audio data.

        Returns:
            Concatenated audio chunks as numpy array
        """
        if not self._chunks:
            return np.array([])
        return np.concatenate(self._chunks)


def resample_audio(audio_data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resample audio to target sample rate.

    Args:
        audio_data: Input audio data
        orig_sr: Original sample rate
        target_sr: Target sample rate

    Returns:
        Resampled audio data
    """
    if orig_sr == target_sr:
        return audio_data

    from scipy import signal

    target_length = int(len(audio_data) * target_sr / orig_sr)
    audio_float = audio_data.astype(np.float32)
    resampled = signal.resample(audio_float, target_length)

    # Convert back to original dtype
    if audio_data.dtype == np.int16:
        return resampled.astype(np.int16)
    return resampled


def normalize_audio(audio_data: np.ndarray) -> np.ndarray:
    """
    Normalize audio data to range [-1.0, 1.0].

    Args:
        audio_data: Input audio data

    Returns:
        Normalized audio data
    """
    max_val = np.max(np.abs(audio_data))
    if max_val == 0:
        return audio_data

    return audio_data / max_val
