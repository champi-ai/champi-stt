"""
Whisper-based wake word detection.

Uses WhisperLive STT to continuously transcribe audio and detect wake words in text.
Less efficient than dedicated wake word models but more reliable.
"""

# import logging - replaced with loguru

import numpy as np
from loguru import logger

from champi_stt.assistant.wakeword.base import BaseWakeWordEngine, WakeWordConfig
from champi_stt.core.base_provider import BaseSTTProvider


class WhisperWakeWordDetector(BaseWakeWordEngine):
    """
    Whisper-based wake word detection.

    Continuously transcribes audio chunks and looks for wake words in transcribed text.
    """

    def __init__(self, config: WakeWordConfig, stt_provider: BaseSTTProvider):
        """
        Initialize Whisper wake word detector.

        Args:
            config: Wake word configuration
            stt_provider: STT provider (should be initialized)
        """
        super().__init__(config)
        self.stt = stt_provider
        self._initialized = False
        self._audio_buffer = []
        self._buffer_duration = 2.0  # Process 2 seconds of audio at a time
        self._last_transcription = ""  # Track last transcription to avoid repeats
        self._min_audio_rms = 100  # Minimum RMS to consider speech (not silence)
        self._last_wake_audio: np.ndarray | None = (
            None  # Store wake word audio for speaker ID
        )

    async def initialize(self) -> None:
        """Initialize Whisper wake word detector"""
        if self._initialized:
            return

        # Verify STT provider is initialized
        if not hasattr(self.stt, "_initialized") or not self.stt._initialized:
            logger.warning("STT provider not initialized, attempting initialization...")
            await self.stt.initialize()

        # Set audio parameters (16kHz for Whisper)
        self.config.sample_rate = 16000
        self.config.frame_length_ms = 80  # 80ms chunks

        self._initialized = True
        logger.info(
            f"✓ WhisperWakeWord initialized: "
            f"sample_rate={self.config.sample_rate}Hz, "
            f"keywords={self.config.keywords}, "
            f"buffer_duration={self._buffer_duration}s"
        )

    async def shutdown(self) -> None:
        """Shutdown Whisper wake word detector"""
        self._audio_buffer.clear()
        self._initialized = False
        logger.info("WhisperWakeWord shutdown complete")

    async def process_audio(self, audio_chunk: np.ndarray) -> tuple[bool, str | None]:
        """
        Process audio chunk for wake word detection.

        Args:
            audio_chunk: Audio data as int16 numpy array

        Returns:
            Tuple of (detected, keyword_detected)
        """
        if not self._initialized:
            return False, None

        try:
            # Add chunk to buffer
            self._audio_buffer.append(audio_chunk)

            # Calculate buffer duration
            total_samples = sum(len(chunk) for chunk in self._audio_buffer)
            buffer_duration_sec = total_samples / self.config.sample_rate

            # Process when buffer reaches target duration
            if buffer_duration_sec >= self._buffer_duration:
                # Concatenate buffer
                full_audio = np.concatenate(self._audio_buffer)

                # Calculate RMS to detect silence
                audio_rms = np.sqrt(np.mean(full_audio.astype(np.float32) ** 2))

                # Skip transcription if audio is too quiet (silence/background noise)
                if audio_rms < self._min_audio_rms:
                    logger.debug(
                        f"Skipping transcription - silence detected (RMS {audio_rms:.1f} < {self._min_audio_rms})"
                    )
                    self._audio_buffer.clear()
                    return False, None

                # Transcribe
                result = await self.stt.transcribe(full_audio)

                # Extract text and metadata
                if isinstance(result, str):
                    text = result
                    no_speech_prob = 0.0
                else:
                    text = result.get("text", "")
                    # no_speech_prob is in segments, not top level
                    segments = result.get("segments", [])
                    if segments:
                        no_speech_prob = segments[0].get("no_speech_prob", 0.0)
                    else:
                        no_speech_prob = 0.0

                text_lower = text.lower().strip()

                # Skip if Whisper detects no speech (hallucination prevention)
                if no_speech_prob > 0.5:
                    logger.debug(
                        f"Skipping hallucination - no speech detected (prob: {no_speech_prob:.2f}): '{text_lower}'"
                    )
                    self._audio_buffer.clear()
                    return False, None

                # Skip if identical to last transcription (repeated hallucination)
                if text_lower and text_lower == self._last_transcription:
                    logger.debug(f"Skipping repeated transcription: '{text_lower}'")
                    self._audio_buffer.clear()
                    return False, None

                # Update last transcription
                self._last_transcription = text_lower

                logger.debug(f"Transcribed: '{text_lower}' (RMS: {audio_rms:.1f})")

                # Check for wake words
                for keyword in self.config.keywords:
                    keyword_lower = keyword.lower().replace("_", " ")
                    if keyword_lower in text_lower:
                        logger.info(
                            f"✓ Wake word detected: '{keyword}' in text '{text_lower}'"
                        )
                        # Store wake word audio for speaker identification
                        self._last_wake_audio = full_audio.copy()
                        self._audio_buffer.clear()
                        self._last_transcription = ""  # Reset after detection
                        return True, keyword

                # Clear buffer
                self._audio_buffer.clear()

            return False, None

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            self._audio_buffer.clear()
            return False, None

    @property
    def sample_rate(self) -> int:
        """Get required sample rate"""
        return 16000

    @property
    def frame_length(self) -> int:
        """Get frame length in samples"""
        # 80ms at 16kHz = 1280 samples
        return int(0.08 * 16000)

    @property
    def is_initialized(self) -> bool:
        """Check if WhisperWakeWord is initialized"""
        return self._initialized

    def get_last_wake_audio(self) -> np.ndarray | None:
        """
        Get the audio from the last wake word detection.

        Returns:
            Audio data from last wake word, or None if no wake word detected yet
        """
        return self._last_wake_audio
