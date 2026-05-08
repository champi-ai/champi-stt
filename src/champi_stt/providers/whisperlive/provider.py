"""
WhisperLive STT Provider
========================

Local STT provider using WhisperLive for direct speech-to-text processing.
Refactored to follow KokoroSvc patterns with async operations, event emission,
and no global state.
"""

import asyncio
import contextlib
import dataclasses

# import logging - replaced with loguru
import queue
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from champi_signals import EventProcessor

try:
    import sounddevice as sd

    SOUNDDEVICE_AVAILABLE = True
except OSError:
    sd = None  # type: ignore[assignment]
    SOUNDDEVICE_AVAILABLE = False
from scipy import signal

from champi_stt.core.response import TranscriptionResponse, TranscriptionSegment
from champi_stt.providers.whisperlive.config import WhisperLiveConfig
from champi_stt.providers.whisperlive.enums import (
    LifecycleEvents,
    LoggingStrings,
    ResponseFormat,
    TaskType,
    WhisperStrings,
)
from champi_stt.providers.whisperlive.events import STTSignalManager
from champi_stt.providers.whisperlive.exceptions import (
    WhisperFileError,
    WhisperInitializationError,
)
from champi_stt.providers.whisperlive.transcriber import WhisperLiveTranscriber

# Optional webrtcvad for silence detection
try:
    import webrtcvad

    VAD_AVAILABLE = True
except ImportError:
    webrtcvad = None
    VAD_AVAILABLE = False

from loguru import logger


@dataclasses.dataclass
class AudioDevice:
    name: str
    device_id: str
    sample_rate: int
    chunk_size: int
    input_channels: int
    output_channels: int


class WhisperLiveSTTProvider:
    """
    Local STT provider using WhisperLive with async singleton pattern.

    Provides direct speech-to-text processing for integration with voice tools.
    Follows KokoroSvc patterns with proper async operations and event emission.
    """

    _instance = None

    def __new__(cls, _logger=None, config: WhisperLiveConfig | None = None):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, _logger=None, config: WhisperLiveConfig | None = None):
        """Initialize singleton instance"""
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.config = config or WhisperLiveConfig.from_env()

        # Configure logging with config level
        from champi_stt.core.logging import configure_logging

        configure_logging(level=self.config.log_level, log_file=self.config.log_file)
        # Note: Directory validation moved to initialize() method

        self.name = "WhisperLive"
        self.transcriber: WhisperLiveTranscriber | None = None
        self._initialized = False
        self._stt_status: LifecycleEvents = LifecycleEvents.UNINITIALIZED.value

        logger.debug(
            f"WhisperLive STT provider created with model: {self.config.model_size}"
        )

    class Meta:
        event_type = "lifecycle"
        signal_manager = STTSignalManager()

    @classmethod
    async def get_instance(
        cls, _logger=None, config: WhisperLiveConfig | None = None
    ) -> "WhisperLiveSTTProvider":
        """Get singleton instance"""
        return cls(_logger=_logger, config=config)

    @EventProcessor.emits_event(data=["_stt_status"])
    async def initialize(self) -> None:
        """Initialize the provider with comprehensive setup."""
        if self._initialized:
            return

        try:
            self._stt_status = LifecycleEvents.INITIALIZING.value

            # Emit initialization start
            self.Meta.signal_manager.lifecycle.send(
                self,
                event_type="lifecycle",
                sub_event="initialization_start",
                data={"model_size": self.config.model_size},
            )

            # 1. Validate directories FIRST
            self.validate_directories()

            # 2. Initialize transcriber (which initializes model manager)
            self.transcriber = WhisperLiveTranscriber(self.config)

            # 3. Emit pre-loading signal
            self.Meta.signal_manager.model.send(
                self,
                event_type="model",
                sub_event="loading_start",
                data={
                    "model_size": self.config.model_size,
                    "device": self.config.device,
                },
            )

            # 4. Initialize model (with caching/device detection)
            await self.transcriber.initialize()

            self._initialized = True
            self._stt_status = LifecycleEvents.READY.value

            # Emit completion
            self.Meta.signal_manager.lifecycle.send(
                self,
                event_type="lifecycle",
                sub_event="initialization_complete",
                data={"initialized": True, "device": self.config.device},
            )

            logger.info(LoggingStrings.PROVIDER_INITIALIZED.value)

        except FileNotFoundError as e:
            logger.error(f"Required files not found: {e}")
            self.Meta.signal_manager.lifecycle.send(
                self,
                event_type="lifecycle",
                sub_event="initialization_error",
                data={"error": str(e)},
            )
            raise WhisperFileError(f"Required files not found: {e}") from e

        except Exception as e:
            logger.error(LoggingStrings.FAILED_TO_INITIALIZE.value.format(e))
            self.Meta.signal_manager.lifecycle.send(
                self,
                event_type="lifecycle",
                sub_event="initialization_error",
                data={"error": str(e)},
            )
            raise WhisperInitializationError(
                f"Provider initialization failed: {e}"
            ) from e

    @EventProcessor.emits_event(data=["config.model_size"])
    async def transcribe(
        self,
        audio_data: bytes | np.ndarray | str,
        language: str | None = None,
        prompt: str | None = None,
        response_format: str = ResponseFormat.JSON.value,
        temperature: float = 0.0,
        word_timestamps: bool = False,
        **kwargs,
    ) -> TranscriptionResponse:
        """
        Transcribe audio data.

        Args:
            audio_data: Audio data (bytes, numpy array, or file path)
            language: Language code for transcription
            prompt: Initial prompt for the model
            response_format: Output format (unused, kept for API compatibility)
            temperature: Sampling temperature
            word_timestamps: Include word-level timestamps
            **kwargs: Additional transcription parameters

        Returns:
            TranscriptionResponse with text, language, and segments
        """
        if not self.transcriber:
            raise RuntimeError(LoggingStrings.PROVIDER_NOT_INITIALIZED.value)

        try:
            logger.info(f"WhisperLive transcribe called with format: {response_format}")
            logger.info(f"Audio data type: {type(audio_data)}")

            # Prepare transcription parameters
            transcribe_params = {
                "language": language,
                "temperature": temperature,
                "word_timestamps": word_timestamps,
                **kwargs,
            }

            if prompt:
                transcribe_params["initial_prompt"] = prompt

            # Transcribe based on input type
            if isinstance(audio_data, Path):
                audio_data = str(audio_data)
            if isinstance(audio_data, str):
                # File path
                logger.info(f"Transcribing from file: {audio_data}")
                result = await self.transcriber.transcribe_audio(
                    audio_data, **transcribe_params
                )
            elif isinstance(audio_data, np.ndarray):
                # Numpy array
                logger.info(
                    f"Transcribing numpy array: shape={audio_data.shape}, dtype={audio_data.dtype}"
                )
                result = await self.transcriber.transcribe_numpy(
                    audio_data, **transcribe_params
                )
            else:
                # Bytes - save to temp file
                logger.info(
                    f"Transcribing bytes data: length={len(audio_data) if hasattr(audio_data, '__len__') else 'unknown'}"
                )
                result = await self._transcribe_bytes(audio_data, transcribe_params)

            # Log raw transcription result
            logger.info(f"Raw transcription result: {result}")
            logger.info(f"Result type: {type(result)}")

            # Format response based on requested format
            return self._format_response(result, response_format)

        except Exception as e:
            logger.error(LoggingStrings.TRANSCRIPTION_FAILED.value.format(e))
            raise

    async def translate(
        self,
        audio_data: bytes | np.ndarray | str,
        prompt: str | None = None,
        response_format: str = ResponseFormat.JSON.value,
        temperature: float = 0.0,
        **kwargs,
    ) -> TranscriptionResponse:
        """
        Translate audio to English.

        Args:
            audio_data: Audio data (bytes, numpy array, or file path)
            prompt: Initial prompt for the model
            response_format: Output format ("json", "text", "verbose_json")
            temperature: Sampling temperature
            **kwargs: Additional transcription parameters

        Returns:
            Translation result in requested format
        """
        return await self.transcribe(
            audio_data,
            language=None,  # Auto-detect
            prompt=prompt,
            response_format=response_format,
            temperature=temperature,
            task=TaskType.TRANSLATE.value,
            **kwargs,
        )

    async def _transcribe_bytes(
        self, audio_data: bytes, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Transcribe audio from bytes by saving to temporary file."""
        import os

        # Create temporary file for audio data
        with tempfile.NamedTemporaryFile(
            suffix=WhisperStrings.WAV_EXTENSION.value, delete=False
        ) as temp_file:
            temp_file.write(audio_data)
            temp_file.flush()

            try:
                # Transcribe using the temporary file
                result = await self.transcriber.transcribe_audio(
                    temp_file.name, **params
                )
                return result
            finally:
                # Clean up temporary file
                with contextlib.suppress(Exception):
                    os.unlink(temp_file.name)

    def _format_response(
        self, result: dict[str, Any], response_format: str
    ) -> TranscriptionResponse:
        """Format transcription response as a TranscriptionResponse."""
        segments = [
            TranscriptionSegment(
                id=i,
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
                text=seg.get("text", ""),
                avg_logprob=seg.get("avg_logprob", 0.0),
                no_speech_prob=seg.get("no_speech_prob", 0.0),
                tokens=seg.get("tokens", []),
                temperature=seg.get("temperature", 0.0),
                compression_ratio=seg.get("compression_ratio", 0.0),
            )
            for i, seg in enumerate(result.get("segments", []))
        ]
        return TranscriptionResponse(
            text=result.get("text", ""),
            language=result.get("language", "unknown"),
            language_probability=result.get("language_probability", 0.0),
            duration=result.get("duration", 0.0),
            segments=segments,
            task=result.get("task", TaskType.TRANSCRIBE.value),
            processing_time=result.get("processing_time", 0.0),
        )

    async def detect_language(
        self, audio_data: str | np.ndarray | bytes, **kwargs
    ) -> tuple[str, float, list[tuple[str, float]]]:
        """
        Detect language of audio.

        Args:
            audio_data: Audio data (file path, numpy array, or bytes)
            **kwargs: Additional parameters for language detection

        Returns:
            Tuple of (language, probability, all_language_probs)
        """
        if not self._initialized:
            await self.initialize()

        if not self.transcriber:
            raise RuntimeError(LoggingStrings.PROVIDER_NOT_INITIALIZED.value)

        if isinstance(audio_data, bytes):
            # Save bytes to temp file and detect
            with tempfile.NamedTemporaryFile(
                suffix=WhisperStrings.WAV_EXTENSION.value, delete=False
            ) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()

                try:
                    return await self.transcriber.detect_language(
                        temp_file.name, **kwargs
                    )
                finally:
                    import os

                    with contextlib.suppress(Exception):
                        os.unlink(temp_file.name)
        else:
            return await self.transcriber.detect_language(audio_data, **kwargs)

    async def get_model_info(self) -> dict[str, Any]:
        """Get information about the loaded model."""
        if not self._initialized:
            return {"status": "not_initialized"}

        if not self.transcriber:
            return {"status": "no_transcriber"}

        return await self.transcriber.get_model_info()

    async def clear_cache(self) -> None:
        """Clear model cache."""
        if self.transcriber:
            await self.transcriber.clear_cache()

    @property
    def is_initialized(self) -> bool:
        """Check if provider is initialized."""
        return self._initialized

    def _get_model_path(self) -> str:
        """Return the model size/path used by this provider."""
        return self.config.model_size

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.transcriber is not None and self.transcriber.is_loaded

    async def save_transcription(
        self, text: str, prefix: str = "stt", metadata: dict | None = None
    ) -> str | None:
        """Save a transcription to the transcriptions directory.

        Args:
            text: The transcription text to save
            prefix: Prefix for the filename (default: 'stt')
            metadata: Optional metadata to include at the top of the file

        Returns:
            Path to the saved file or None if saving is disabled
        """
        if self.transcriber:
            return await self.transcriber.save_transcription(text, prefix, metadata)
        return None

    def validate_directories(self) -> None:
        """Validate and create directories if needed (provider-owned)"""
        import os

        # Set defaults if not specified
        if not self.config.cache_dir:
            self.config.cache_dir = self.get_default_cache_dir()
        if self.config.save_transcriptions and not self.config.transcriptions_dir:
            self.config.transcriptions_dir = self.get_default_transcriptions_dir()

        # Create all directories
        try:
            Path(self.config.cache_dir).mkdir(parents=True, exist_ok=True)
            if self.config.save_transcriptions:
                expanded_trans_dir = os.path.expanduser(self.config.transcriptions_dir)
                Path(expanded_trans_dir).mkdir(parents=True, exist_ok=True)
                self.config.transcriptions_dir = expanded_trans_dir

            logger.debug(
                f"Directories validated - Cache: {self.config.cache_dir}, "
                f"Transcriptions: {self.config.transcriptions_dir if self.config.save_transcriptions else 'disabled'}"
            )
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            raise WhisperFileError(f"Directory creation failed: {e}") from e

    def get_default_cache_dir(self) -> str:
        """Get platform-appropriate cache directory"""
        import os

        home = Path.home()
        if os.name == "nt":  # Windows
            app_data = os.environ.get("APPDATA", home)
            return str(Path(app_data) / "mcp_champi" / "whisper" / "cache")
        else:  # Unix-like
            return str(home / ".mcp_champi" / "whisper" / "cache")

    def get_default_transcriptions_dir(self) -> str:
        """Get platform-appropriate transcriptions directory"""
        import os

        home = Path.home()
        if os.name == "nt":  # Windows
            app_data = os.environ.get("APPDATA", home)
            return str(Path(app_data) / "mcp_champi" / "whisper" / "transcriptions")
        else:  # Unix-like
            return str(home / ".mcp_champi" / "whisper" / "transcriptions")

    def get_audio_device(self, device_name: str) -> AudioDevice:
        """Initialize audio device settings

        Args:
            device_name: Name of the audio device to find

        Returns:
            AudioDevice configuration
        """
        # Find audio device
        devices = sd.query_devices()

        device_raw = next(
            (d for i, d in enumerate(devices) if device_name in d["name"]), None
        )

        if device_raw is None:
            raise ValueError(f"Could not find audio device: {device_name}")

        device_sample_rate = int(device_raw["default_samplerate"])
        device_id = device_raw["index"]
        chunk_size = 1024
        _device = AudioDevice(
            name=device_raw["name"],
            device_id=device_id,
            sample_rate=device_sample_rate,  # Use device's native sample rate
            chunk_size=chunk_size,
            input_channels=device_raw["max_input_channels"],
            output_channels=device_raw["max_output_channels"],
        )

        logger.debug(f"Using audio device: {_device}")
        return _device

    async def record_audio(self, duration: float) -> np.ndarray:
        """Record audio from microphone for fixed duration

        Args:
            duration: Recording duration in seconds

        Returns:
            Audio data as numpy array
        """
        logger.debug(LoggingStrings.RECORDING_AUDIO.value.format(duration))

        try:
            # Get the configured audio device (not default!)
            device_name = (
                self.config.input_device or WhisperStrings.USB_MIC_DEVICE.value
            )
            audio_device = self.get_audio_device(device_name)

            samples_to_record = int(duration * audio_device.sample_rate)

            loop = asyncio.get_running_loop()
            recording = await loop.run_in_executor(
                None,
                lambda: sd.rec(
                    frames=samples_to_record,
                    samplerate=audio_device.sample_rate,
                    channels=1,
                    dtype=np.int16,
                    device=audio_device.device_id,
                ),
            )
            await loop.run_in_executor(None, sd.wait)

            flattened = recording.flatten()
            logger.debug(
                LoggingStrings.AUDIO_RECORDED.value.format(len(flattened), duration)
            )

            # Calculate RMS level for debugging
            if hasattr(self.config, "debug") and self.config.debug:
                rms = np.sqrt(np.mean(flattened.astype(float) ** 2))
                logger.debug(f"RMS level: {rms:.2f}")

            return flattened

        except Exception as e:
            logger.error(LoggingStrings.RECORDING_FAILED.value.format(e))
            return np.array([])

    async def record_audio_with_silence_detection(
        self, max_duration: float, disable_silence_detection: bool = False
    ) -> np.ndarray:
        """Record audio from microphone with automatic silence detection.

        Args:
            max_duration: Maximum recording duration in seconds
            disable_silence_detection: Whether to disable silence detection

        Returns:
            Audio data as numpy array
        """
        if (
            not VAD_AVAILABLE
            or self.config.disable_silence_detection
            or disable_silence_detection
        ):
            logger.debug("Using fixed duration recording")
            return await self.record_audio(max_duration)

        logger.debug(LoggingStrings.RECORDING_WITH_VAD.value.format(max_duration))

        try:
            return await self._record_with_vad(max_duration)
        except Exception as e:
            logger.error(LoggingStrings.VAD_INITIALIZATION_FAILED.value.format(e))
            logger.debug("Falling back to fixed duration recording")
            return await self.record_audio(max_duration)

    async def _record_with_vad(self, max_duration: float) -> np.ndarray:
        """Record audio with VAD in async context."""
        # Initialize VAD
        vad = webrtcvad.Vad(int(self.config.vad_aggressiveness))

        # Calculate chunk size
        chunk_duration_s = self.config.vad_chunk_duration_ms / 1000

        # VAD sample rate (16kHz for compatibility)
        vad_sample_rate = 16000

        vad_chunk_samples = int(
            vad_sample_rate * self.config.vad_chunk_duration_ms / 1000
        )
        # Recording state
        chunks = []
        silence_duration_ms = 0
        recording_duration = 0
        stop_recording = False

        # VAD processing buffer - accumulate chunks before processing
        vad_buffer = []

        audio_queue = queue.Queue(maxsize=-1)

        def audio_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio stream status: {status}")
            audio_queue.put(indata.copy())

        try:
            # Use configured input device or fall back to hardcoded USB mic
            device_name = (
                self.config.input_device or WhisperStrings.USB_MIC_DEVICE.value
            )
            _mic_device = self.get_audio_device(device_name=device_name)
            mic_stream = sd.InputStream(
                samplerate=_mic_device.sample_rate,
                channels=_mic_device.input_channels,
                dtype=np.int16,
                callback=audio_callback,
                blocksize=_mic_device.chunk_size,
            )

            logger.debug(f"Audio stream {mic_stream}")
            with mic_stream:
                logger.debug("Audio stream started")
                while recording_duration < max_duration and not stop_recording:
                    try:
                        chunk = await asyncio.get_running_loop().run_in_executor(
                            None, lambda: audio_queue.get(timeout=0.1)
                        )
                        chunk_flat = chunk.flatten()
                        chunks.append(chunk_flat)

                        # Add to VAD buffer for accumulation
                        vad_buffer.extend(chunk_flat)

                        # Calculate buffer target size (500ms of audio for better VAD performance)
                        vad_buffer_target_samples = int(_mic_device.sample_rate * 0.5)

                        # Process VAD only when we have enough buffered audio
                        if len(vad_buffer) < vad_buffer_target_samples:
                            recording_duration += chunk_duration_s
                            print(
                                f"Skipping - buffer: {len(vad_buffer)}/{vad_buffer_target_samples}, queue: {audio_queue.qsize()}"
                            )
                            continue

                        # Take buffered audio for VAD processing
                        buffered_audio = np.array(
                            vad_buffer[:vad_buffer_target_samples]
                        )
                        vad_buffer = vad_buffer[
                            vad_buffer_target_samples:
                        ]  # Keep remainder

                        # VAD processing - resample from device rate to 16kHz for VAD
                        device_rate = _mic_device.sample_rate
                        if device_rate != vad_sample_rate:
                            # Proper resampling from device rate to 16kHz for VAD
                            try:
                                # Calculate target length for resampling buffered audio
                                target_length = int(
                                    len(buffered_audio) * vad_sample_rate / device_rate
                                )

                                # Convert to float for resampling to avoid clipping
                                buffered_float = buffered_audio.astype(np.float32)
                                resampled_float = signal.resample(
                                    buffered_float, target_length
                                )

                                # Convert back to int16 with proper scaling
                                resampled_chunk = resampled_float.astype(np.int16)

                                # Ensure we have EXACTLY the right number of samples for VAD
                                # WebRTC VAD requires precise frame sizes
                                if len(resampled_chunk) >= vad_chunk_samples:
                                    vad_chunk = resampled_chunk[:vad_chunk_samples]
                                else:
                                    # Pad with zeros if too short
                                    vad_chunk = np.zeros(
                                        vad_chunk_samples, dtype=np.int16
                                    )
                                    vad_chunk[: len(resampled_chunk)] = resampled_chunk

                            except ImportError:
                                # Fallback to decimation if scipy not available
                                logger.warning(
                                    "scipy not available, using decimation fallback for VAD"
                                )
                                downsample_ratio = device_rate // vad_sample_rate
                                decimated_chunk = chunk_flat[::downsample_ratio]
                                if len(decimated_chunk) >= vad_chunk_samples:
                                    vad_chunk = decimated_chunk[:vad_chunk_samples]
                                else:
                                    # Pad with zeros if too short
                                    vad_chunk = np.zeros(
                                        vad_chunk_samples, dtype=np.int16
                                    )
                                    vad_chunk[: len(decimated_chunk)] = decimated_chunk
                        else:
                            # Same sample rate, just ensure correct size
                            if len(chunk_flat) >= vad_chunk_samples:
                                vad_chunk = chunk_flat[:vad_chunk_samples]
                            else:
                                # Pad with zeros if too short
                                vad_chunk = np.zeros(vad_chunk_samples, dtype=np.int16)
                                vad_chunk[: len(chunk_flat)] = chunk_flat
                        chunk_bytes = vad_chunk.tobytes()

                        # Debug VAD chunk properties
                        chunk_rms = np.sqrt(np.mean(vad_chunk.astype(float) ** 2))
                        logger.debug(
                            f"VAD chunk: {len(vad_chunk)} samples, RMS: {chunk_rms:.2f}, max: {np.max(np.abs(vad_chunk))}"
                        )

                        try:
                            is_speech = vad.is_speech(chunk_bytes, vad_sample_rate)
                            if is_speech:
                                logger.debug(
                                    f"🗣️ SPEECH detected! RMS: {chunk_rms:.2f}, silence_ms: {silence_duration_ms}"
                                )
                            else:
                                logger.debug(
                                    f"🤫 No speech detected, RMS: {chunk_rms:.2f}, silence_ms: {silence_duration_ms}"
                                )
                        except Exception as vad_e:
                            logger.warning(f"VAD error: {vad_e}, treating as speech")
                            is_speech = True

                        if is_speech:
                            # if not speech_detected:
                            #     logger.debug(LoggingStrings.SPEECH_DETECTED_START.value)
                            silence_duration_ms = 0
                        else:
                            silence_duration_ms += self.config.vad_chunk_duration_ms
                            if silence_duration_ms % 1000 == 0:  # Log every second
                                pass  # Silence detected logging removed
                        # recording_duration += chunk_duration_s

                        # # Check stop conditions
                        # if (
                        #     speech_detected
                        #     and recording_duration >= self.config.min_recording_duration
                        # ) and silence_duration_ms >= self.config.silence_threshold_ms:
                        #     logger.debug(LoggingStrings.SILENCE_DETECTED_STOP.value.format(recording_duration))
                        #     stop_recording = True

                        # if (
                        #     not speech_detected
                        #     and recording_duration >= self.config.initial_silence_grace_period
                        # ):
                        #     logger.debug(LoggingStrings.NO_SPEECH_DETECTED.value.format(self.config.initial_silence_grace_period))
                        #     stop_recording = True

                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.error(f"Error processing audio chunk: {e}")
                        break

            # Concatenate all chunks
            if chunks:
                full_recording = np.concatenate(chunks)
                logger.debug(
                    LoggingStrings.AUDIO_RECORDED.value.format(
                        len(full_recording), recording_duration
                    )
                )
                return full_recording
            else:
                logger.warning(LoggingStrings.EMPTY_AUDIO_CHUNKS.value)
                return np.array([])

        except Exception as e:
            logger.error(f"Recording with VAD failed: {e}")
            logger.debug("Falling back to fixed duration recording")
            return await self.record_audio(max_duration)

    async def speech_to_text(
        self,
        audio_data: np.ndarray,
        save_audio: bool = False,
        audio_dir: str | None = None,
    ) -> str | None:
        """
        Speech to text using integrated WhisperLive.

        Args:
            audio_data: Audio data as numpy array
            save_audio: Whether to save audio (currently unused, handled by config)
            audio_dir: Audio directory (currently unused, handled by config)

        Returns:
            Transcribed text or None if failed
        """
        try:
            if not self.is_loaded:
                logger.error(LoggingStrings.MODEL_NOT_LOADED.value)
                return None

            logger.info("Using integrated WhisperLive STT")

            logger.info(
                f"Sending audio data to WhisperLive: shape={audio_data.shape}, dtype={audio_data.dtype}"
            )
            logger.info(
                f"Using sample rate: {self.config.sample_rate} Hz for WhisperLive"
            )

            # Use the actual device sample rate for transcription, not config sample rate
            device_name = (
                self.config.input_device or WhisperStrings.USB_MIC_DEVICE.value
            )
            audio_device = self.get_audio_device(device_name)
            actual_sample_rate = audio_device.sample_rate

            logger.info(
                f"Transcribing with sample rate: {actual_sample_rate} Hz (not config: {self.config.sample_rate})"
            )
            try:
                result = await self.transcribe(
                    audio_data=audio_data,
                    response_format=ResponseFormat.TEXT.value,
                    sample_rate=actual_sample_rate,  # Use actual device sample rate
                )
            except Exception as e:
                logger.error(f"Transcription failed: {e}")

            # Enhanced logging for debugging STT responses
            logger.info(f"Raw WhisperLive STT response: {result}")
            logger.info(f"Response type: {type(result)}")

            if isinstance(result, dict):
                logger.info(f"Dict keys: {list(result.keys())}")
                if "text" in result:
                    text = result["text"].strip()
                    logger.debug(f"Extracted text from dict: '{text}'")
                else:
                    logger.warning(
                        f"No 'text' key in response dict. Available keys: {list(result.keys())}"
                    )
                    text = None
            elif isinstance(result, str):
                text = result.strip()
                logger.info(f"Direct string response: '{text}'")
            else:
                logger.info(
                    f"Unexpected response type: {type(result)}, value: {result}"
                )
                text = None

            if text:
                logger.info(f"✓ WhisperLive STT result: '{text}' (length: {len(text)})")

                # Save transcription using provider's save method
                from datetime import datetime

                metadata = {
                    "type": "stt",
                    "model": "whisperlive",
                    "provider": "whisperlive-local",
                    "timestamp": datetime.now().isoformat(),
                }
                await self.save_transcription(text, prefix="stt", metadata=metadata)

                return text
            else:
                logger.warning(LoggingStrings.EMPTY_TRANSCRIPTION.value.format(result))
                return None

        except Exception as e:
            import traceback

            logger.error(LoggingStrings.TRANSCRIPTION_FAILED.value.format(e))
            logger.error(
                f"WhisperLive STT exception traceback: {traceback.format_exc()}"
            )
            logger.debug(
                f"Audio data info - shape: {audio_data.shape if audio_data is not None else 'None'}, "
                f"dtype: {audio_data.dtype if audio_data is not None else 'None'}"
            )
            return None

    async def shutdown(self) -> None:
        """Shutdown the provider and clean up resources."""

        if self.transcriber:
            await self.transcriber.shutdown()
            self.transcriber = None

        self._initialized = False
        logger.debug(LoggingStrings.PROVIDER_UNLOADED.value)


WhisperLiveProvider = WhisperLiveSTTProvider


if __name__ == "__main__":
    from tests.test_whisper_vad_recording import run_all_vad_tests

    try:
        asyncio.run(run_all_vad_tests())
    except KeyboardInterrupt:
        print("\n👋 VAD testing interrupted. Goodbye!")
