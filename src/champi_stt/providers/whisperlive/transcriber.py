"""
WhisperLive Transcriber
======================

Core transcription functionality extracted from WhisperLive for local STT processing.
Refactored to remove global state and use async patterns with event emission.
"""

import asyncio
import io
import logging
import os
import tempfile
import time
from typing import Any

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from champi_stt.providers.whisperlive.config import WhisperLiveConfig
from champi_stt.providers.whisperlive.enums import LoggingStrings, ProcessingEvents, LifecycleEvents, ModelEvents
from champi_stt.providers.whisperlive.events import STTSignalManager
from champi_stt.providers.whisperlive.exceptions import WhisperTranscriptionError, WhisperAudioError
from champi_signals import EventProcessor
from champi_stt.providers.whisperlive.models import ModelManager

logger = logging.getLogger(__name__)


class WhisperLiveTranscriber:
    """
    WhisperLive transcriber for local speech-to-text processing.

    Provides optimized transcription using faster-whisper with VAD,
    batching, and device optimization. Refactored to remove global state
    and use async patterns with comprehensive event emission.
    """

    def __init__(self, config: WhisperLiveConfig | None = None):
        """Initialize transcriber with configuration."""
        self.config = config or WhisperLiveConfig.from_env()
        self.model_manager = ModelManager(self.config)
        self._initialized = False

        logger.debug(
            f"Initializing WhisperLive transcriber: "
            f"model={self.config.model_size}, "
            f"device={self.config.device}, "
            f"compute_type={self.config.compute_type}"
        )
    
    class Meta:
        event_type = 'processing'
        signal_manager = STTSignalManager()

    async def initialize(self) -> None:
        """Initialize the transcriber and load the model."""
        if self._initialized:
            return

        # Emit initialization start event
        self.Meta.signal_manager.lifecycle.send(
            self,
            event_type="lifecycle",
            sub_event="transcriber_initialization_start",
            data={"model_size": self.config.model_size}
        )

        # Initialize model manager
        await self.model_manager.initialize()
        self._initialized = True

        # Emit initialization complete event
        self.Meta.signal_manager.lifecycle.send(
            self,
            event_type="lifecycle",
            sub_event="transcriber_initialization_complete",
            data={
                "initialized": True,
                "model_size": self.config.model_size,
                "device": self.config.device
            }
        )

        logger.debug("WhisperLive transcriber initialized successfully")

    @property
    def model(self) -> WhisperModel | None:
        """Get the loaded model instance."""
        return self.model_manager.model if self.model_manager else None

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model_manager.is_loaded if self.model_manager else False

    @EventProcessor.emits_event(data=["config.model_size", "config.device"])
    async def transcribe_audio(
        self,
        audio: str | np.ndarray | io.BytesIO | io.BufferedReader,
        language: str | None = None,
        task: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Transcribe audio using WhisperLive.

        Args:
            audio: Audio data (file path, numpy array, or file-like object)
            language: Language code (overrides config)
            task: Task type (overrides config)
            **kwargs: Additional transcription parameters

        Returns:
            Dictionary with transcription results
        """

        start_time = time.time()

        # Emit audio received event
        self.Meta.signal_manager.processing.send(
            self,
            event_type="processing",
            sub_event="audio_received",
            data={
                "audio_type": type(audio).__name__,
                "model_size": self.config.model_size,
                "device": self.config.device
            }
        )

        # Use config defaults if not provided
        language = language or self.config.get_effective_language()
        task = task or self.config.task

        # Prepare transcription parameters
        transcribe_params = {
            "language": language,
            "task": task,
            "beam_size": self.config.beam_size,
            "best_of": self.config.best_of,
            "temperature": self.config.temperature,
            "compression_ratio_threshold": self.config.compression_ratio_threshold,
            "log_prob_threshold": self.config.log_prob_threshold,
            "no_speech_threshold": self.config.no_speech_threshold,
            "vad_filter": False,
            "vad_parameters": self.config.vad_parameters,
            "word_timestamps": self.config.word_timestamps,
            "chunk_length": self.config.chunk_length,
        }

        # Override with any provided kwargs
        transcribe_params.update(kwargs)
        logger.debug(f"Transcribing audio with parameters: {transcribe_params}")

        # Emit transcription start event
        self.Meta.signal_manager.processing.send(
            self,
            event_type="processing",
            sub_event="transcription_start",
            data={
                "language": language,
                "task": task,
                "model_size": self.config.model_size
            }
        )

        try:
            # Perform transcription in executor to avoid blocking event loop
            loop = asyncio.get_running_loop()
            segments, info = await loop.run_in_executor(
                None, lambda: self.model.transcribe(audio, **transcribe_params)
            )

            logger.debug(f"segments = {segments}")
            logger.debug(f"info = {info}")
            # Convert segments to list
            segment_list = self._process_segments(segments)

            # Prepare response
            transcription_time = time.time() - start_time

            response = {
                "text": " ".join(segment["text"] for segment in segment_list),
                "segments": segment_list,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "duration_after_vad": info.duration_after_vad,
                "processing_time": transcription_time,
            }

            # Emit transcription complete event
            rtf = transcription_time / info.duration if info.duration > 0 else 0
            self.Meta.signal_manager.processing.send(
                self,
                event_type="processing",
                sub_event="transcription_complete",
                data={
                    "text": response["text"],
                    "language": info.language,
                    "language_probability": info.language_probability,
                    "duration": info.duration,
                    "processing_time": transcription_time,
                    "rtf": rtf,
                    "segment_count": len(segment_list)
                }
            )

            # Emit telemetry event with performance metrics
            self.Meta.signal_manager.telemetry.send(
                self,
                event_type="telemetry",
                sub_event="performance_stats",
                data={
                    "model_size": self.config.model_size,
                    "device": self.config.device,
                    "audio_duration": info.duration,
                    "audio_duration_after_vad": info.duration_after_vad,
                    "processing_time": transcription_time,
                    "rtf": rtf,
                    "segment_count": len(segment_list),
                    "language": info.language,
                    "language_probability": info.language_probability,
                    "beam_size": self.config.beam_size,
                    "batch_size": self.config.batch_size,
                    "vad_enabled": self.config.vad_filter,
                    "word_timestamps": self.config.word_timestamps
                }
            )

            logger.debug(
                f"Transcribed {info.duration:.2f}s audio in {transcription_time:.2f}s "
                f"(RTF: {rtf:.2f})"
            )

            return response

        except Exception as e:
            logger.error(LoggingStrings.TRANSCRIPTION_FAILED.value.format(e))

            # Emit error event
            self.Meta.signal_manager.processing.send(
                self,
                event_type="processing",
                sub_event="transcription_error",
                data={"error": str(e), "audio_type": type(audio).__name__}
            )

            raise WhisperTranscriptionError(f"Transcription failed: {e}") from e

    def _process_segments(self, segments) -> list[dict[str, Any]]:
        """Process transcription segments asynchronously."""
        segment_list = []
        
        for segment in segments:
            segment_data = {
                "id": segment.id,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "avg_logprob": segment.avg_logprob,
                "no_speech_prob": segment.no_speech_prob,
                "compression_ratio": segment.compression_ratio,
                "temperature": segment.temperature,
                "tokens": segment.tokens,
            }

            if segment.words:
                segment_data["words"] = [
                    {
                        "start": word.start,
                        "end": word.end,
                        "word": word.word,
                        "probability": word.probability,
                    }
                    for word in segment.words
                ]

            segment_list.append(segment_data)

        return segment_list

    async def play_audio(
        self, audio: str | np.ndarray | io.BytesIO | io.BufferedReader, sample_rate: int = 44100
    ) -> None:
        """
        Play the audio data for verification purposes.

        Args:
            audio: Audio data (file path, numpy array, or file-like object)
            sample_rate: Sample rate of the audio data (default: 44100)
        """
        logger.debug("Playing audio for verification...")

        # Emit playback start event
        self.Meta.signal_manager.processing.send(
            self,
            event_type="processing",
            sub_event="audio_playback_start",
            data={
                "audio_type": type(audio).__name__,
                "sample_rate": sample_rate
            }
        )

        try:
            audio_data = await self._load_audio_data(audio, sample_rate)

            if audio_data is not None:
                await self._play_audio_data(audio_data, sample_rate)

                # Emit playback complete event
                self.Meta.signal_manager.processing.send(
                    self,
                    event_type="processing",
                    sub_event="audio_playback_complete",
                    data={
                        "duration": len(audio_data) / sample_rate,
                        "sample_rate": sample_rate
                    }
                )
            else:
                logger.error("Failed to load audio data for playback")

                # Emit error event
                self.Meta.signal_manager.processing.send(
                    self,
                    event_type="processing",
                    sub_event="audio_playback_error",
                    data={"error": "Failed to load audio data"}
                )

                raise WhisperAudioError("Failed to load audio data for playback")

        except Exception as e:
            logger.error(LoggingStrings.AUDIO_PLAYBACK_FAILED.value.format(e))

            # Emit error event
            self.Meta.signal_manager.processing.send(
                self,
                event_type="processing",
                sub_event="audio_playback_error",
                data={"error": str(e)}
            )

            raise WhisperAudioError(f"Audio playback failed: {e}") from e

    async def _load_audio_data(self, audio, sample_rate: int) -> np.ndarray | None:
        """Load audio data from various input types."""
        loop = asyncio.get_running_loop()
        
        if isinstance(audio, str):
            # Load from file path
            import librosa
            audio_data, _ = await loop.run_in_executor(
                None, lambda: librosa.load(audio, sr=sample_rate, mono=True)
            )
            logger.debug(f"Loaded audio from file: {audio}, shape={audio_data.shape}")
            return audio_data

        elif isinstance(audio, np.ndarray):
            # Already a numpy array
            logger.debug(f"Using provided numpy array, shape={audio.shape}")
            return audio

        elif hasattr(audio, "read"):
            # File-like object
            import librosa
            
            with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
                content = await loop.run_in_executor(None, audio.read)
                await loop.run_in_executor(None, tmp.write, content)
                tmp.flush()
                audio_data, _ = await loop.run_in_executor(
                    None, lambda: librosa.load(tmp.name, sr=sample_rate, mono=True)
                )
                logger.debug(f"Loaded audio from file-like object, shape={audio_data.shape}")
                return audio_data
        
        return None

    async def _play_audio_data(self, audio_data: np.ndarray, sample_rate: int) -> None:
        """Play audio data using sounddevice."""
        # Normalize if needed
        if np.max(np.abs(audio_data)) > 1.0:
            audio_data = audio_data / np.max(np.abs(audio_data))

        # Play audio using sounddevice
        loop = asyncio.get_running_loop()
        
        try:
            # Try PulseAudio device first (allows mixing with other apps)
            await loop.run_in_executor(
                None,
                lambda: (sd.play(audio_data, sample_rate, device="pulse"), sd.wait())
            )
        except Exception as pulse_error:
            logger.debug(f"PulseAudio device failed: {pulse_error}, trying default")
            try:
                # Fallback to default device
                await loop.run_in_executor(
                    None,
                    lambda: (sd.play(audio_data, sample_rate), sd.wait())
                )
            except Exception as default_error:
                logger.error(LoggingStrings.AUDIO_PLAYBACK_FAILED.value.format(default_error))

                # Emit error event
                self.Meta.signal_manager.processing.send(
                    self,
                    event_type="processing",
                    sub_event="audio_playback_error",
                    data={"error": str(default_error), "device": "default"}
                )

                raise WhisperAudioError(f"Audio playback failed on default device: {default_error}") from default_error

        logger.debug("Audio playback completed")

    @EventProcessor.emits_event(data=["config.model_size"])
    async def transcribe_numpy(
        self, audio_data: np.ndarray, sample_rate: int = 16000, **kwargs
    ) -> dict[str, Any]:
        """
        Transcribe numpy array audio data.

        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of audio data
            **kwargs: Additional transcription parameters

        Returns:
            Dictionary with transcription results
        """

        # Emit audio received event
        self.Meta.signal_manager.processing.send(
            self,
            event_type="processing",
            sub_event="audio_received",
            data={
                "audio_type": "numpy",
                "shape": audio_data.shape,
                "dtype": str(audio_data.dtype),
                "sample_rate": sample_rate,
                "duration": len(audio_data) / sample_rate
            }
        )

        # Emit preprocessing start event
        self.Meta.signal_manager.processing.send(
            self,
            event_type="processing",
            sub_event="audio_preprocessing",
            data={
                "original_sample_rate": sample_rate,
                "target_sample_rate": 16000,
                "needs_resampling": sample_rate != 16000
            }
        )

        # Ensure audio is in correct format for faster-whisper
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Normalize if needed
        if audio_data.max() > 1.0:
            audio_data = audio_data / np.max(np.abs(audio_data))

        # Resample if needed (faster-whisper expects 16kHz)
        if sample_rate != 16000:
            from scipy import signal
            audio_data = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: signal.resample(
                    audio_data, int(len(audio_data) * 16000 / sample_rate)
                ).astype(np.float32)
            )

        # Emit preprocessing complete event
        self.Meta.signal_manager.processing.send(
            self,
            event_type="processing",
            sub_event="audio_normalized",
            data={
                "final_shape": audio_data.shape,
                "final_dtype": str(audio_data.dtype),
                "final_sample_rate": 16000
            }
        )

        return await self.transcribe_audio(audio_data, **kwargs)

    @EventProcessor.emits_event(data=["config.model_size"])
    async def detect_language(
        self, audio: str | np.ndarray | io.BytesIO | io.BufferedReader, **kwargs
    ) -> tuple[str, float, list[tuple[str, float]]]:
        """
        Detect language of audio.

        Args:
            audio: Audio data (file path, numpy array, or file-like object)
            **kwargs: Additional parameters for language detection

        Returns:
            Tuple of (language, probability, all_language_probs)
        """
        if not self._initialized:
            await self.initialize()

        # Emit language detection start
        self.Meta.signal_manager.processing.send(
            self,
            event_type="processing",
            sub_event="language_detection_start",
            data={
                "audio_type": type(audio).__name__,
                "model_size": self.config.model_size
            }
        )

        try:

            # Execute language detection in thread pool
            loop = asyncio.get_running_loop()

            if isinstance(audio, str):
                import librosa
                audio_data, _ = await loop.run_in_executor(
                    None, lambda: librosa.load(audio, sr=44100, mono=True)
                )
                result = await loop.run_in_executor(
                    None, lambda: self.model.detect_language(audio_data, **kwargs)
                )
            else:
                result = await loop.run_in_executor(
                    None, lambda: self.model.detect_language(audio, **kwargs)
                )

            language, probability, all_probs = result

            # Emit language detected event
            self.Meta.signal_manager.processing.send(
                self,
                event_type="processing",
                sub_event="language_detected",
                data={
                    "language": language,
                    "probability": probability,
                    "top_languages": all_probs[:5] if all_probs else []
                }
            )

            logger.debug(LoggingStrings.LANGUAGE_DETECTED.value.format(language, probability))

            return result

        except Exception as e:
            logger.error(LoggingStrings.LANGUAGE_DETECTION_FAILED.value.format(e))

            # Emit error event
            self.Meta.signal_manager.processing.send(
                self,
                event_type="processing",
                sub_event="language_detection_error",
                data={"error": str(e)}
            )

            raise WhisperTranscriptionError(f"Language detection failed: {e}") from e

    async def get_model_info(self) -> dict[str, Any]:
        """Get information about the loaded model."""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        return await self.model_manager.get_model_info()

    async def clear_cache(self) -> None:
        """Clear model cache."""
        if self.model_manager:
            await self.model_manager.clear_cache()
        logger.debug("Model cache cleared")

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
        from datetime import datetime
        from pathlib import Path

        # Check if transcription saving is enabled in config
        if not self.config.save_transcriptions:
            return None

        # Emit save start event
        self.Meta.signal_manager.processing.send(
            self,
            event_type="processing",
            sub_event="transcription_save_start",
            data={
                "text_length": len(text),
                "has_metadata": metadata is not None,
                "prefix": prefix
            }
        )

        try:
            # Get transcriptions directory from config
            transcriptions_dir = os.path.expanduser(self.config.transcriptions_dir)

            # Ensure directory exists
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: Path(transcriptions_dir).mkdir(parents=True, exist_ok=True)
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"{prefix}_{timestamp}.txt"
            filepath = Path(transcriptions_dir) / filename

            content = []

            # Add metadata header if provided
            if metadata:
                content.extend([
                    "=" * 50,
                    "TRANSCRIPTION METADATA",
                    "=" * 50,
                ])
                for key, value in metadata.items():
                    content.append(f"{key}: {value}")
                content.extend(["=" * 50, ""])

            # Add transcription text
            content.append(text)

            # Write to file asynchronously
            file_content = "\n".join(content)
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: filepath.write_text(file_content, encoding="utf-8")
            )

            logger.debug(LoggingStrings.TRANSCRIPTION_SAVED.value.format(filepath))

            # Emit save complete event
            self.Meta.signal_manager.processing.send(
                self,
                event_type="processing",
                sub_event="transcription_save_complete",
                data={
                    "filepath": str(filepath),
                    "filename": filename,
                    "size_bytes": len(file_content.encode("utf-8"))
                }
            )

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to save transcription: {e}")

            # Emit error event
            self.Meta.signal_manager.processing.send(
                self,
                event_type="processing",
                sub_event="transcription_save_error",
                data={"error": str(e)}
            )

            raise WhisperAudioError(f"Failed to save transcription: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown the transcriber and clean up resources."""

        # Emit shutdown start event
        self.Meta.signal_manager.lifecycle.send(
            self,
            event_type="lifecycle",
            sub_event="transcriber_shutdown_start",
            data={"initialized": self._initialized}
        )

        if self.model_manager:
            await self.model_manager.unload()

        self._initialized = False

        # Emit shutdown complete event
        self.Meta.signal_manager.lifecycle.send(
            self,
            event_type="lifecycle",
            sub_event="transcriber_shutdown_complete",
            data={"initialized": False}
        )

        logger.debug("WhisperLive transcriber shut down")