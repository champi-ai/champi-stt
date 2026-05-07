"""
Main voice assistant service daemon
"""

import asyncio
import contextlib

# import logging - replaced with loguru
import os
import subprocess
import sys
from enum import Enum

# AudioStream is defined in this module below
from loguru import logger

from champi_stt.assistant.commands.registry import CommandRegistry
from champi_stt.assistant.ipc import (
    AssistantSharedMemoryManager,
    AssistantSignalManager,
    AssistantSignalProcessor,
    AssistantSignalType,
    cleanup_orphaned_regions,
)
from champi_stt.assistant.service.config import AssistantConfig
from champi_stt.assistant.wakeword.base import BaseWakeWordEngine
from champi_stt.core.base_provider import BaseSTTProvider


class ServiceState(Enum):
    """Voice assistant service states"""

    IDLE = "idle"
    INITIALIZING = "initializing"
    LISTENING_FOR_WAKE = "listening_for_wake"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    EXECUTING_COMMAND = "executing_command"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class AudioStream:
    """
    Continuous audio streaming for real-time processing.

    Yields audio chunks asynchronously for wake word detection.
    """

    def __init__(
        self, sample_rate: int = 16000, chunk_size: int = 512, device: int | None = None
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device = device
        self._running = False
        self._stream = None
        self._queue = None

    async def __aiter__(self):
        """Async iterator yielding audio chunks"""
        import queue

        import numpy as np
        import sounddevice as sd

        self._queue = queue.Queue()
        self._callback_count = 0

        def callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio stream status: {status}")
            self._callback_count += 1
            if self._callback_count <= 3:
                logger.debug(
                    f"Audio callback #{self._callback_count}: {frames} frames, range [{indata.min():.0f}, {indata.max():.0f}]"
                )
            if self._queue:
                self._queue.put(indata.copy())

        self._running = True

        # Configure for shared access (non-exclusive)
        # Use higher latency to allow device sharing
        stream_kwargs = {
            "samplerate": self.sample_rate,
            "channels": 1,
            "dtype": np.int16,
            "blocksize": self.chunk_size,
            "callback": callback,
            "device": self.device,
            "latency": "high",  # Allow shared access with higher latency
        }

        # Create stream without context manager so we can close it explicitly
        self._stream = sd.InputStream(**stream_kwargs)
        self._stream.start()

        try:
            while self._running and self._stream and self._stream.active:
                try:
                    chunk = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self._queue.get(timeout=0.1)
                    )
                    yield chunk.flatten()
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Audio stream error: {e}")
                    break
        finally:
            # Clean up stream
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    logger.debug(f"Error closing stream: {e}")
                self._stream = None

    def stop(self):
        """Stop the audio stream"""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.debug(f"Error stopping stream: {e}")
            self._stream = None


class AssistantService:
    """
    Main voice assistant service daemon.

    Coordinates:
    - Wake word detection
    - STT transcription
    - Command execution
    """

    def __init__(
        self,
        config: AssistantConfig,
        stt_provider: BaseSTTProvider,
        wakeword_engine: BaseWakeWordEngine,
        command_registry: CommandRegistry,
        enable_visualizer: bool = False,
    ):
        self.config = config
        self.stt = stt_provider
        self.wakeword = wakeword_engine
        self.commands = command_registry
        self.enable_visualizer = enable_visualizer

        self.state = ServiceState.IDLE
        self._running = False
        self._audio_stream: AudioStream | None = None
        self._visualizer = None
        self._speaker_identifier = None
        self._recording_mode = False  # Flag to prevent stream restart during recording

        # IPC components for wake indicator
        self._signal_manager = None
        self._memory_manager = None
        self._signal_processor = None
        self._ui_process = None
        self._memory_prefix = os.getenv(
            "CHAMPI_ASSISTANT_MEMORY_PREFIX", "champi_assistant"
        )
        # Initialize IPC and wake indicator if enabled
        if self.config.enable_wake_indicator:
            self.status_indicator()

        # Initialize speaker identification if enabled
        if self.config.enable_speaker_identification:
            self.speaker_identification()

    def status_indicator(self):

        try:
            # Initialize signal manager
            self._signal_manager = AssistantSignalManager()

            # Initialize shared memory manager
            self._memory_manager = AssistantSharedMemoryManager(
                name_prefix=self._memory_prefix
            )

            # Initialize signal processor
            self._signal_processor = AssistantSignalProcessor(self._memory_manager)

            # Connect signals to processor with data mappers
            self._signal_processor.connect_signal(
                self._signal_manager.state,
                AssistantSignalType.STATE_CHANGE,
                data_mapper=lambda **kw: {
                    "state": kw.get("sub_event", "")
                    .replace("_START", "")
                    .replace("_FINISH", "")
                    .lower()
                },
            )

            # Connect additional signal types
            self._signal_processor.connect_signal(
                self._signal_manager.processing,
                AssistantSignalType.WAKE_DETECTED,
                data_mapper=lambda **kw: (
                    {"wake_word": kw.get("wake_word", "")}
                    if kw.get("sub_event") == "WAKE_DETECTED"
                    else None
                ),
            )

            self._signal_processor.connect_signal(
                self._signal_manager.processing,
                AssistantSignalType.RECORDING,
                data_mapper=lambda **kw: (
                    {
                        "duration": kw.get("duration", 0.0),
                        "is_active": kw.get("is_active", False),
                    }
                    if "RECORDING" in kw.get("sub_event", "")
                    else None
                ),
            )

            self._signal_processor.connect_signal(
                self._signal_manager.processing,
                AssistantSignalType.TRANSCRIBING,
                data_mapper=lambda **kw: (
                    {
                        "partial_text": kw.get("text", ""),
                        "is_final": kw.get("is_final", False),
                    }
                    if "TRANSCRIBING" in kw.get("sub_event", "")
                    else None
                ),
            )

            self._signal_processor.connect_signal(
                self._signal_manager.processing,
                AssistantSignalType.EXECUTING,
                data_mapper=lambda **kw: (
                    {"command": kw.get("command", "")}
                    if "EXECUTING" in kw.get("sub_event", "")
                    else None
                ),
            )

            self._signal_processor.connect_signal(
                self._signal_manager.error,
                AssistantSignalType.ERROR,
                data_mapper=lambda **kw: {
                    "error_message": kw.get("error", ""),
                    "error_type": kw.get("error_type", ""),
                },
            )

            # Clean up any orphaned regions from previous crashes
            cleaned = cleanup_orphaned_regions(name_prefix=self._memory_prefix)
            if cleaned:
                logger.info(f"Cleaned up {len(cleaned)} orphaned shared memory regions")

            # Create shared memory regions
            self._memory_manager.create_regions()
            logger.info(
                f"Created {len(self._memory_manager.memory_regions)} shared memory regions"
            )

            # Start signal processor
            self._signal_processor.start()
            logger.info("Signal processor started")

            # Launch UI subprocess if enabled
            ui_enabled = (
                os.getenv("CHAMPI_ASSISTANT_UI_ENABLED", "true").lower() == "true"
            )
            if ui_enabled:
                self._launch_ui_subprocess()
            else:
                logger.info("UI subprocess disabled by configuration")

            logger.info(
                f"Wake indicator IPC initialized with prefix: {self._memory_prefix}"
            )
        except Exception as e:
            logger.warning(f"Wake indicator requested but initialization failed: {e}")

    def speaker_identification(self):
        try:
            from champi_stt.assistant.speaker import SpeakerIdentifier

            self._speaker_identifier = SpeakerIdentifier()
            logger.info(
                f"Speaker identification enabled with {len(self._speaker_identifier.profiles)} enrolled speakers"
            )
        except ImportError as e:
            logger.warning(
                f"Speaker identification requested but resemblyzer not available: {e}"
            )
            self._speaker_identifier = None
        except Exception as e:
            logger.error(f"Failed to initialize speaker identification: {e}")
            self._speaker_identifier = None

        logger.info("Voice assistant service created")

    def _set_state(self, new_state: ServiceState):
        """Set state and emit signal for wake indicator"""
        self.state = new_state
        if self._signal_manager:
            # Emit state change signal
            self._signal_manager.state.send(
                event_type="state",
                sub_event=f"{new_state.value.upper()}_START",
                data={"state": new_state.value},
            )

    def _launch_ui_subprocess(self):
        """Launch wake indicator UI subprocess"""
        try:
            # Get path to wake_indicator_ui.py
            import champi_stt.assistant.ui.wake_indicator_ui as ui_module

            ui_script = ui_module.__file__

            # Setup log file for UI subprocess
            import pathlib

            cache_dir = pathlib.Path(self.config.cache_dir).expanduser()
            cache_dir.mkdir(parents=True, exist_ok=True)
            ui_log_file = cache_dir / "ui.log"

            # Open log file
            log_handle = open(ui_log_file, "a")  # noqa: SIM115

            # Launch subprocess with logging
            self._ui_process = subprocess.Popen(
                [sys.executable, ui_script, self._memory_prefix],
                start_new_session=True,
                stdout=log_handle,
                stderr=log_handle,
            )
            self._ui_log_handle = log_handle  # Keep handle for cleanup
            logger.info(
                f"Wake indicator UI subprocess launched (PID: {self._ui_process.pid})"
            )
            logger.info(f"UI logs: {ui_log_file}")
        except Exception as e:
            logger.error(f"Failed to launch UI subprocess: {e}")

    async def start(self):
        """Start the assistant service"""
        logger.info("Starting voice assistant service...")

        try:
            self._set_state(ServiceState.INITIALIZING)

            # Initialize STT provider
            logger.info("Initializing STT provider...")
            await self.stt.initialize()

            # Initialize wake word engine
            logger.info("Initializing wake word engine...")
            await self.wakeword.initialize()

            # Register wake word callback
            self.wakeword.on_detection(self._on_wake_word)

            self._running = True
            self._set_state(ServiceState.LISTENING_FOR_WAKE)

            logger.info("✓ Voice assistant service started")
            logger.info(f"Listening for wake words: {self.config.wakeword_keywords}")

            # Start listening loop
            await self._listen_loop()

        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            self._set_state(ServiceState.ERROR)

            # Send SHUTDOWN signal to UI on critical error
            if self._signal_manager and self._ui_process:
                try:
                    self._signal_manager.emit(
                        AssistantSignalType.SHUTDOWN, reason="error"
                    )
                    logger.info("Sent SHUTDOWN signal to UI (error)")
                    await asyncio.sleep(0.2)
                except Exception as shutdown_error:
                    logger.warning(f"Failed to send SHUTDOWN signal: {shutdown_error}")

            raise

    async def _listen_loop(self):
        """Main listening loop for wake word detection"""
        import numpy as np
        import sounddevice as sd
        from scipy import signal

        from champi_stt.core.audio import get_audio_device

        # Get audio device if configured
        device_id = None
        wakeword_sample_rate = self.wakeword.config.sample_rate
        wakeword_frame_samples = (
            self.wakeword.get_frame_length_samples()
        )  # 1280 samples @ 16kHz

        if self.config.input_device:
            try:
                audio_device = get_audio_device(self.config.input_device)
                device_id = audio_device.device_id
                device_sample_rate = audio_device.sample_rate
                logger.info(f"Using audio input device: {audio_device.name}")
                logger.info(f"  Sample rate: {device_sample_rate} Hz")
                logger.info(f"  Channels: {audio_device.input_channels}")
            except ValueError as e:
                logger.warning(
                    f"Could not find device '{self.config.input_device}': {e}, using default"
                )
                device_sample_rate = wakeword_sample_rate
        else:
            # Get default device info
            try:
                default_device = sd.query_devices(kind="input")
                device_sample_rate = int(default_device["default_samplerate"])
                logger.info(f"Using default input device: {default_device['name']}")
                logger.info(f"  Sample rate: {device_sample_rate} Hz")
            except Exception as e:
                logger.warning(
                    f"Could not query default device: {e}, using config values"
                )
                device_sample_rate = wakeword_sample_rate

        # Calculate device chunk size to match wake word requirements after resampling
        # We need wakeword_frame_samples at wakeword_sample_rate after resampling
        device_chunk_size = int(
            wakeword_frame_samples * device_sample_rate / wakeword_sample_rate
        )

        # Determine if resampling is needed
        needs_resampling = device_sample_rate != wakeword_sample_rate

        if needs_resampling:
            logger.info(
                f"Audio will be resampled from {device_sample_rate} Hz to {wakeword_sample_rate} Hz"
            )
            logger.info(
                f"  Device chunk: {device_chunk_size} samples → Wake word frame: {wakeword_frame_samples} samples"
            )

        # Main loop - recreate stream when it stops (e.g., for command recording)
        while self._running:
            logger.debug("Creating audio stream for wake word detection...")
            self._audio_stream = AudioStream(
                sample_rate=device_sample_rate,
                chunk_size=device_chunk_size,
                device=device_id,
            )

            try:
                async for audio_chunk in self._audio_stream:
                    if not self._running:
                        break

                    # Only process wake words when in listening state
                    if self.state == ServiceState.LISTENING_FOR_WAKE:
                        # Resample if needed
                        if needs_resampling:
                            # Calculate target length for resampling
                            target_length = int(
                                len(audio_chunk)
                                * wakeword_sample_rate
                                / device_sample_rate
                            )

                            # Convert to float for resampling
                            audio_float = audio_chunk.astype(np.float32)

                            # Resample
                            resampled_float = signal.resample(
                                audio_float, target_length
                            )

                            # Convert back to int16
                            resampled_chunk = resampled_float.astype(np.int16)

                            # Debug first chunk and periodically check audio levels
                            if not hasattr(self, "_logged_resample"):
                                logger.debug(
                                    f"Resampling: {len(audio_chunk)} → {len(resampled_chunk)} samples"
                                )
                                logger.debug(
                                    f"  Input range: [{audio_chunk.min()}, {audio_chunk.max()}]"
                                )
                                logger.debug(
                                    f"  Output range: [{resampled_chunk.min()}, {resampled_chunk.max()}]"
                                )
                                self._logged_resample = True
                                self._audio_check_counter = 0

                            # Check audio levels periodically
                            self._audio_check_counter = (
                                getattr(self, "_audio_check_counter", 0) + 1
                            )
                            if self._audio_check_counter >= 50:  # Every ~2 seconds
                                rms = np.sqrt(
                                    np.mean(resampled_chunk.astype(np.float32) ** 2)
                                )
                                logger.debug(
                                    f"Audio RMS level: {rms:.1f} (range: [{resampled_chunk.min()}, {resampled_chunk.max()}])"
                                )
                                self._audio_check_counter = 0
                        else:
                            resampled_chunk = audio_chunk

                        # Add to visualizer if enabled
                        if self._visualizer:
                            self._visualizer.add_audio(resampled_chunk)

                        # Emit audio level data for UI visualization
                        if self._signal_manager:
                            try:
                                from champi_stt.assistant.audio_analysis import (
                                    analyze_audio_chunk,
                                )

                                rms_db, dominant_freq, is_speaking = (
                                    analyze_audio_chunk(
                                        resampled_chunk,
                                        sample_rate=wakeword_sample_rate,
                                    )
                                )
                                self._signal_manager.processing.send(
                                    event_type="processing",
                                    sub_event="AUDIO_LEVEL",
                                    data={
                                        "rms_db": rms_db,
                                        "dominant_freq": dominant_freq,
                                        "is_speaking": is_speaking,
                                    },
                                )
                            except Exception as e:
                                # Don't log every failure, just first few
                                if not hasattr(self, "_audio_analysis_errors"):
                                    self._audio_analysis_errors = 0
                                if self._audio_analysis_errors < 3:
                                    logger.debug(f"Audio analysis error: {e}")
                                    self._audio_analysis_errors += 1

                        await self.wakeword.process_audio_with_callback(resampled_chunk)

            except Exception as e:
                logger.error(f"Listen loop error: {e}")
                self._set_state(ServiceState.ERROR)
                break  # Exit outer loop on error

            # Stream has stopped (e.g., for command recording)
            # Wait a moment before restarting
            if self._running:
                logger.debug("Audio stream stopped, will restart after delay...")
                await asyncio.sleep(0.5)

    async def _on_wake_word(self, keyword: str):
        """
        Handle wake word detection.

        Args:
            keyword: Detected wake word
        """
        logger.info(f"🎤 Wake word detected: '{keyword}'")

        # Play wake detection audio feedback
        try:
            from champi_stt.assistant.audio_feedback import play_audio_feedback

            await play_audio_feedback("wake", enabled=True)
        except Exception as e:
            logger.debug(f"Audio feedback failed: {e}")

        # Emit wake detected signal
        if self._signal_manager:
            self._signal_manager.processing.send(
                event_type="processing",
                sub_event="WAKE_DETECTED",
                data={"wake_word": keyword},
            )

        # Identify speaker from wake word audio if enabled
        speaker_name = None
        speaker_confidence = 0.0

        if self._speaker_identifier and hasattr(self.wakeword, "get_last_wake_audio"):
            wake_audio = self.wakeword.get_last_wake_audio()
            if wake_audio is not None and len(wake_audio) > 0:
                speaker_name, speaker_confidence = (
                    self._speaker_identifier.identify_speaker(
                        wake_audio,
                        threshold=self.config.speaker_identification_threshold,
                    )
                )

        try:
            # Stop the audio stream to release microphone for recording
            logger.info("Stopping wake word audio stream...")
            if self._audio_stream:
                self._audio_stream.stop()
                # Wait for stream to fully close and release device
                await asyncio.sleep(0.5)
                logger.debug("Audio stream closed")

            # Transition to recording state
            self._set_state(ServiceState.RECORDING)

            # Emit recording start signal
            if self._signal_manager:
                self._signal_manager.processing.send(
                    event_type="processing",
                    sub_event="RECORDING_START",
                    data={"duration": 0.0, "is_active": True},
                )

            # Record user command (with VAD for automatic silence detection)
            logger.info("Recording command...")

            # Play listening chime before recording
            try:
                from champi_stt.assistant.audio_feedback import play_audio_feedback

                await play_audio_feedback("listening", enabled=True)
            except Exception as e:
                logger.debug(f"Audio feedback failed: {e}")

            from champi_stt.core.audio import record_audio_with_vad

            audio = await record_audio_with_vad(
                max_duration=self.config.max_recording_duration,
                device_name=self.config.input_device,
                sample_rate=16000,
                silence_threshold_ms=self.config.command_silence_timeout_ms,
            )

            # Play finished chime after recording
            try:
                from champi_stt.assistant.audio_feedback import play_audio_feedback

                await play_audio_feedback("finished", enabled=True)
            except Exception as e:
                logger.debug(f"Audio feedback failed: {e}")

            if len(audio) == 0:
                logger.warning("No audio recorded")
                self._set_state(ServiceState.LISTENING_FOR_WAKE)
                return

            # Transcribe command
            self._set_state(ServiceState.TRANSCRIBING)
            logger.info("Transcribing command...")

            # Emit transcribing signal
            if self._signal_manager:
                self._signal_manager.processing.send(
                    event_type="processing",
                    sub_event="TRANSCRIBING_START",
                    data={"partial_text": "Processing...", "is_final": False},
                )

            result = await self.stt.transcribe(audio)
            text = result if isinstance(result, str) else result.get("text", "")

            if not text:
                logger.warning("Empty transcription")
                self._set_state(ServiceState.LISTENING_FOR_WAKE)
                return

            logger.info(f"Transcription: '{text}'")

            # Emit final transcription
            if self._signal_manager:
                self._signal_manager.processing.send(
                    event_type="processing",
                    sub_event="TRANSCRIBING_FINISH",
                    data={"partial_text": text, "is_final": True},
                )

            # Execute command with speaker context
            self._set_state(ServiceState.EXECUTING_COMMAND)

            # Emit executing signal
            if self._signal_manager:
                self._signal_manager.processing.send(
                    event_type="processing",
                    sub_event="EXECUTING_START",
                    data={"command": text},
                )
            context = {}
            if speaker_name:
                context["speaker"] = speaker_name
                context["speaker_confidence"] = speaker_confidence

            command_result = await self.commands.execute(text, context=context)

            if command_result:
                logger.info(f"✓ Command executed: {command_result}")

                # Check for shutdown command
                if (
                    isinstance(command_result, dict)
                    and command_result.get("action") == "shutdown"
                ):
                    logger.info("Shutdown requested")
                    await self.stop()
                    return
            else:
                logger.info(f"No matching command for: '{text}'")

        except Exception as e:
            logger.error(f"Error handling wake word: {e}")
            self._set_state(ServiceState.ERROR)

            # Emit error signal
            if self._signal_manager:
                self._signal_manager.error.send(
                    event_type="error",
                    sub_event="ERROR",
                    data={"error": str(e), "error_type": type(e).__name__},
                )

        finally:
            # Return to listening state (if continuous mode)
            if self.config.continuous_mode and self._running:
                self._set_state(ServiceState.LISTENING_FOR_WAKE)

    async def stop(self):
        """Stop the assistant service"""
        logger.info("Stopping voice assistant service...")

        self._running = False
        self._set_state(ServiceState.SHUTDOWN)

        # Send SHUTDOWN signal to UI before terminating
        if self._signal_manager and self._ui_process:
            try:
                self._signal_manager.emit(AssistantSignalType.SHUTDOWN, reason="normal")
                logger.info("Sent SHUTDOWN signal to UI")
                # Give UI time to process shutdown signal and cleanup
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"Failed to send SHUTDOWN signal: {e}")

        # Terminate UI subprocess and wait for it to fully exit
        if self._ui_process:
            try:
                self._ui_process.terminate()
                self._ui_process.wait(timeout=3)  # Increased timeout
                logger.info("UI subprocess terminated")
                # Extra wait for process cleanup
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.warning(f"Error terminating UI subprocess: {e}")
                try:
                    self._ui_process.kill()
                    self._ui_process.wait(timeout=1)
                except Exception:
                    pass
            self._ui_process = None

        # Stop signal processor
        if self._signal_processor:
            self._signal_processor.stop()
            self._signal_processor = None
            logger.info("Signal processor stopped")

        # Close UI log handle
        if hasattr(self, "_ui_log_handle"):
            with contextlib.suppress(Exception):
                self._ui_log_handle.close()

        # Cleanup shared memory
        if self._memory_manager:
            self._memory_manager.cleanup()
            self._memory_manager = None
            logger.info("Shared memory cleaned up")

        # Stop visualizer
        if self._visualizer:
            self._visualizer.stop()
            self._visualizer = None

        # Stop audio stream
        if self._audio_stream:
            self._audio_stream.stop()

        # Shutdown components
        await self.wakeword.shutdown()
        await self.stt.shutdown()

        logger.info("✓ Voice assistant service stopped")

    def get_status(self) -> dict:
        """
        Get current service status.

        Returns:
            Status dictionary
        """
        return {
            "state": self.state.value,
            "running": self._running,
            "stt_provider": self.config.stt_provider,
            "wakeword_engine": self.config.wakeword_engine,
            "wakeword_keywords": self.config.wakeword_keywords,
            "continuous_mode": self.config.continuous_mode,
            "commands_registered": len(self.commands),
        }
