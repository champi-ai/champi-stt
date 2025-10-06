"""
Main voice assistant service daemon
"""

import asyncio
import logging
from enum import Enum
from typing import Optional

from champi_stt.core.base_provider import BaseSTTProvider
from champi_stt.assistant.wakeword.base import BaseWakeWordEngine
from champi_stt.assistant.commands.registry import CommandRegistry
from champi_stt.assistant.service.config import AssistantConfig
from champi_stt.core.audio import AudioStream

logger = logging.getLogger(__name__)


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

    def __init__(self, sample_rate: int = 16000, chunk_size: int = 512):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._running = False

    async def __aiter__(self):
        """Async iterator yielding audio chunks"""
        import sounddevice as sd
        import numpy as np
        import queue

        q = queue.Queue()

        def callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio stream status: {status}")
            q.put(indata.copy())

        self._running = True

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.int16,
            blocksize=self.chunk_size,
            callback=callback
        ):
            while self._running:
                try:
                    chunk = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: q.get(timeout=0.1)
                    )
                    yield chunk.flatten()
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Audio stream error: {e}")
                    break

    def stop(self):
        """Stop the audio stream"""
        self._running = False


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
    ):
        self.config = config
        self.stt = stt_provider
        self.wakeword = wakeword_engine
        self.commands = command_registry

        self.state = ServiceState.IDLE
        self._running = False
        self._audio_stream: Optional[AudioStream] = None

        logger.info("Voice assistant service created")

    async def start(self):
        """Start the assistant service"""
        logger.info("Starting voice assistant service...")

        try:
            self.state = ServiceState.INITIALIZING

            # Initialize STT provider
            logger.info("Initializing STT provider...")
            await self.stt.initialize()

            # Initialize wake word engine
            logger.info("Initializing wake word engine...")
            await self.wakeword.initialize()

            # Register wake word callback
            self.wakeword.on_detection(self._on_wake_word)

            self._running = True
            self.state = ServiceState.LISTENING_FOR_WAKE

            logger.info("✓ Voice assistant service started")
            logger.info(f"Listening for wake words: {self.config.wakeword_keywords}")

            # Start listening loop
            await self._listen_loop()

        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            self.state = ServiceState.ERROR
            raise

    async def _listen_loop(self):
        """Main listening loop for wake word detection"""
        self._audio_stream = AudioStream(
            sample_rate=self.wakeword.config.sample_rate,
            chunk_size=self.wakeword.get_frame_length_samples()
        )

        try:
            async for audio_chunk in self._audio_stream:
                if not self._running:
                    break

                # Only process wake words when in listening state
                if self.state == ServiceState.LISTENING_FOR_WAKE:
                    await self.wakeword.process_audio_with_callback(audio_chunk)

        except Exception as e:
            logger.error(f"Listen loop error: {e}")
            self.state = ServiceState.ERROR

    async def _on_wake_word(self, keyword: str):
        """
        Handle wake word detection.

        Args:
            keyword: Detected wake word
        """
        logger.info(f"🎤 Wake word detected: '{keyword}'")

        try:
            # Transition to recording state
            self.state = ServiceState.RECORDING

            # Record user command (with VAD for automatic silence detection)
            logger.info("Recording command...")
            audio = await self.stt.record_audio_with_vad(
                max_duration=self.config.max_recording_duration
            )

            if len(audio) == 0:
                logger.warning("No audio recorded")
                self.state = ServiceState.LISTENING_FOR_WAKE
                return

            # Transcribe command
            self.state = ServiceState.TRANSCRIBING
            logger.info("Transcribing command...")

            result = await self.stt.transcribe(audio)
            text = result if isinstance(result, str) else result.get("text", "")

            if not text:
                logger.warning("Empty transcription")
                self.state = ServiceState.LISTENING_FOR_WAKE
                return

            logger.info(f"Transcription: '{text}'")

            # Execute command
            self.state = ServiceState.EXECUTING_COMMAND
            command_result = await self.commands.execute(text)

            if command_result:
                logger.info(f"✓ Command executed: {command_result}")

                # Check for shutdown command
                if isinstance(command_result, dict) and command_result.get("action") == "shutdown":
                    logger.info("Shutdown requested")
                    await self.stop()
                    return
            else:
                logger.info(f"No matching command for: '{text}'")

        except Exception as e:
            logger.error(f"Error handling wake word: {e}")
            self.state = ServiceState.ERROR

        finally:
            # Return to listening state (if continuous mode)
            if self.config.continuous_mode and self._running:
                self.state = ServiceState.LISTENING_FOR_WAKE

    async def stop(self):
        """Stop the assistant service"""
        logger.info("Stopping voice assistant service...")

        self._running = False
        self.state = ServiceState.SHUTDOWN

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
