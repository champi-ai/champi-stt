"""
Base transcriber interface
"""

from abc import ABC, abstractmethod
from typing import Any
import numpy as np
import io


class BaseTranscriber(ABC):
    """
    Abstract base class for transcriber implementations.

    Transcribers handle the low-level transcription logic for each provider.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the transcriber (load models, etc)"""
        pass

    @abstractmethod
    async def transcribe_audio(
        self,
        audio: str | np.ndarray | io.BytesIO | io.BufferedReader,
        language: str | None = None,
        task: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Transcribe audio data.

        Args:
            audio: Audio data (file path, numpy array, or file-like object)
            language: Language code
            task: Task type ("transcribe" or "translate")
            **kwargs: Provider-specific parameters

        Returns:
            Dictionary with transcription results (format varies by provider)
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup resources"""
        pass

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if transcriber is ready"""
        pass

    # Optional methods

    async def transcribe_numpy(
        self, audio_data: np.ndarray, sample_rate: int = 16000, **kwargs
    ) -> dict[str, Any]:
        """
        Transcribe numpy array audio data.

        Default implementation just calls transcribe_audio.
        Providers can override for custom preprocessing.
        """
        return await self.transcribe_audio(audio_data, **kwargs)

    async def detect_language(
        self, audio: str | np.ndarray | io.BytesIO | io.BufferedReader, **kwargs
    ) -> tuple[str, float, list[tuple[str, float]]]:
        """
        Detect language of audio.

        Returns:
            Tuple of (language, probability, all_language_probs)

        Default implementation returns ("en", 1.0, []).
        """
        return ("en", 1.0, [])

    async def get_model_info(self) -> dict[str, Any]:
        """Get transcriber/model information"""
        return {"status": "loaded" if self.is_loaded else "not_loaded"}
