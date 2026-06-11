"""
Vosk-based wake word / keyword spotting engine.

Uses Vosk's KaldiRecognizer with grammar-constrained decoding to detect
specific keywords without requiring an API key or internet connection.
"""

import json

import numpy as np
from loguru import logger

from champi_stt.assistant.wakeword.base import BaseWakeWordEngine, WakeWordConfig

try:
    from vosk import KaldiRecognizer, Model  # type: ignore[import-untyped]

    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

    class Model:  # type: ignore[no-redef]
        pass

    class KaldiRecognizer:  # type: ignore[no-redef]
        pass


class VoskWakeWord(BaseWakeWordEngine):
    """
    Vosk-based keyword spotting for offline wake word detection.

    Unlike Porcupine, Vosk requires no API key and runs entirely offline.
    Accuracy is lower than dedicated wake word engines for short phrases,
    but it is suitable for development, testing, and privacy-sensitive deployments.

    Requires: vosk library and a Vosk model directory
    Install: pip install vosk
    Models: https://alphacephei.com/vosk/models (download a small model, e.g. vosk-model-small-en-us)

    Usage:
        config = WakeWordConfig(
            keywords=["hey champi", "stop"],
            model_path="/path/to/vosk-model-small-en-us",
        )
        engine = VoskWakeWord(config)
        await engine.initialize()
        detected, keyword = await engine.process_audio(audio_chunk)
    """

    def __init__(self, config: WakeWordConfig) -> None:
        if not VOSK_AVAILABLE:
            raise ImportError(
                "Vosk is not installed. Install with: pip install vosk\n"
                "Download a model from: https://alphacephei.com/vosk/models"
            )
        super().__init__(config)
        self._model: Model | None = None
        self._recognizer: KaldiRecognizer | None = None

    async def initialize(self) -> None:
        """Load the Vosk model and build a grammar-constrained recognizer."""
        if self._initialized:
            return

        if not self.config.model_path:
            raise ValueError(
                "VoskWakeWord requires model_path in WakeWordConfig. "
                "Download a model from https://alphacephei.com/vosk/models and set model_path."
            )

        logger.info(f"Loading Vosk model from: {self.config.model_path}")

        try:
            self._model = Model(self.config.model_path)

            # Build a grammar that only accepts the configured keywords plus silence.
            # This dramatically reduces false positives compared to full ASR.
            grammar = json.dumps([*self.config.keywords, "[unk]"])
            self._recognizer = KaldiRecognizer(
                self._model, self.config.sample_rate, grammar
            )
            self._recognizer.SetWords(False)

            self._initialized = True
            logger.info(
                f"Vosk wake word engine initialized with keywords: {self.config.keywords}"
            )
        except Exception as exc:
            logger.error(f"Failed to initialize Vosk: {exc}")
            raise RuntimeError(f"Vosk initialization failed: {exc}") from exc

    async def process_audio(self, audio_chunk: np.ndarray) -> tuple[bool, str | None]:
        """
        Feed a chunk of audio to the recognizer and check for keyword matches.

        Args:
            audio_chunk: Audio data as int16 or float32 numpy array.
                         Will be converted to int16 PCM if needed.

        Returns:
            (detected, keyword) — keyword is the matched phrase or None.
        """
        if not self._initialized or self._recognizer is None:
            raise RuntimeError("VoskWakeWord not initialized. Call initialize() first.")

        pcm = self._to_int16_bytes(audio_chunk)

        if self._recognizer.AcceptWaveform(pcm):
            result = json.loads(self._recognizer.Result())
            text = result.get("text", "").strip().lower()
        else:
            partial = json.loads(self._recognizer.PartialResult())
            text = partial.get("partial", "").strip().lower()

        if not text or text == "[unk]":
            return False, None

        for keyword in self.config.keywords:
            if keyword.lower() in text:
                logger.debug(f"Wake word detected: '{keyword}' (text='{text}')")
                return True, keyword

        return False, None

    async def shutdown(self) -> None:
        """Release Vosk model resources."""
        self._recognizer = None
        self._model = None
        self._initialized = False
        logger.debug("Vosk wake word engine shut down")

    @property
    def is_initialized(self) -> bool:
        return self._initialized and self._recognizer is not None

    @staticmethod
    def _to_int16_bytes(audio: np.ndarray) -> bytes:
        """Convert numpy array to int16 PCM bytes as Vosk expects."""
        if audio.dtype == np.float32 or audio.dtype == np.float64:
            audio = (audio * 32767).clip(-32768, 32767).astype(np.int16)
        elif audio.dtype != np.int16:
            audio = audio.astype(np.int16)
        return audio.tobytes()
