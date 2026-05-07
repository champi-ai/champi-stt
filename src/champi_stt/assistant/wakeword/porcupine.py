"""
Porcupine wake word detection engine
"""

import logging

import numpy as np

from champi_stt.assistant.wakeword.base import BaseWakeWordEngine, WakeWordConfig

logger = logging.getLogger(__name__)

try:
    import pvporcupine

    PORCUPINE_AVAILABLE = True
except ImportError:
    pvporcupine = None
    PORCUPINE_AVAILABLE = False


class PorcupineWakeWord(BaseWakeWordEngine):
    """
    Porcupine wake word detection engine.

    Requires: pvporcupine library
    Install: pip install pvporcupine

    Features:
    - High accuracy
    - Low resource usage
    - Cross-platform (Windows, macOS, Linux, Pi)
    - Commercial-friendly licensing

    Usage:
        config = WakeWordConfig(
            keywords=["hey champi"],
            access_key="YOUR_PICOVOICE_ACCESS_KEY",
            sensitivity=0.5
        )
        engine = PorcupineWakeWord(config)
        await engine.initialize()
    """

    def __init__(self, config: WakeWordConfig):
        if not PORCUPINE_AVAILABLE:
            raise ImportError(
                "Porcupine not available. Install with: pip install pvporcupine"
            )

        super().__init__(config)
        self._porcupine: pvporcupine.Porcupine | None = None

    async def initialize(self) -> None:
        """Initialize Porcupine engine"""
        if self._initialized:
            return

        try:
            logger.info(f"Initializing Porcupine with keywords: {self.config.keywords}")

            # Prepare keyword paths (built-in or custom)
            keyword_paths = self._get_keyword_paths()

            # Create Porcupine instance
            self._porcupine = pvporcupine.create(
                access_key=self.config.access_key,
                keyword_paths=keyword_paths,
                sensitivities=[self.config.sensitivity] * len(self.config.keywords),
            )

            # Update sample rate from Porcupine's requirement
            self.config.sample_rate = self._porcupine.sample_rate
            self.config.frame_length_ms = int(
                (self._porcupine.frame_length / self._porcupine.sample_rate) * 1000
            )

            self._initialized = True
            logger.info(
                f"✓ Porcupine initialized: "
                f"sample_rate={self._porcupine.sample_rate}Hz, "
                f"frame_length={self._porcupine.frame_length} samples"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Porcupine: {e}")
            raise RuntimeError(f"Porcupine initialization failed: {e}") from e

    async def process_audio(self, audio_chunk: np.ndarray) -> tuple[bool, str | None]:
        """
        Process audio chunk for wake word detection.

        Args:
            audio_chunk: Audio data as int16 numpy array

        Returns:
            (detected, keyword) tuple
        """
        if not self._initialized or not self._porcupine:
            raise RuntimeError("Porcupine not initialized")

        # Ensure audio is int16
        if audio_chunk.dtype != np.int16:
            audio_chunk = (audio_chunk * 32767).astype(np.int16)

        # Ensure correct frame length
        required_samples = self._porcupine.frame_length
        if len(audio_chunk) < required_samples:
            # Pad with zeros if too short
            padded = np.zeros(required_samples, dtype=np.int16)
            padded[: len(audio_chunk)] = audio_chunk
            audio_chunk = padded
        elif len(audio_chunk) > required_samples:
            # Truncate if too long
            audio_chunk = audio_chunk[:required_samples]

        # Process with Porcupine
        try:
            keyword_index = self._porcupine.process(audio_chunk)

            if keyword_index >= 0:
                keyword = self.config.keywords[keyword_index]
                logger.debug(
                    f"🎤 Detected wake word: '{keyword}' (index={keyword_index})"
                )
                return True, keyword

            return False, None

        except Exception as e:
            logger.error(f"Porcupine processing error: {e}")
            return False, None

    async def shutdown(self) -> None:
        """Cleanup Porcupine resources"""
        if self._porcupine:
            try:
                self._porcupine.delete()
                logger.debug("Porcupine engine shut down")
            except Exception as e:
                logger.error(f"Error shutting down Porcupine: {e}")
            finally:
                self._porcupine = None
                self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if Porcupine is initialized"""
        return self._initialized and self._porcupine is not None

    def _get_keyword_paths(self) -> list[str]:
        """
        Get keyword file paths (built-in or custom).

        Returns:
            List of .ppn file paths
        """
        # If custom model path provided, use it
        if self.config.model_path:
            return [self.config.model_path] * len(self.config.keywords)

        # Otherwise, use built-in keywords
        # Porcupine supports built-in keywords: "alexa", "americano", "blueberry",
        # "bumblebee", "computer", "grapefruit", "grasshopper", "hey google",
        # "hey siri", "jarvis", "ok google", "picovoice", "porcupine", "terminator"

        keyword_paths = []
        for keyword in self.config.keywords:
            # Map common keywords to Porcupine built-ins
            normalized = keyword.lower().strip()

            if normalized in ["jarvis", "computer", "porcupine", "bumblebee", "alexa"]:
                keyword_paths.append(pvporcupine.KEYWORDS[normalized])
            else:
                # For custom keywords, you need to train them via Picovoice Console
                # and provide the .ppn file path
                raise ValueError(
                    f"Keyword '{keyword}' is not a built-in Porcupine keyword. "
                    f"Available built-in keywords: {list(pvporcupine.KEYWORDS.keys())}. "
                    f"For custom keywords, train at https://console.picovoice.ai "
                    f"and provide model_path in config."
                )

        return keyword_paths
