"""
Base transcriber interface
"""

import io
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

import numpy as np

from champi_stt.core.response import TranscriptionChunk


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
        **kwargs: Any,
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
        self, audio_data: np.ndarray, sample_rate: int = 16000, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Transcribe numpy array audio data.

        Default implementation just calls transcribe_audio.
        Providers can override for custom preprocessing.
        """
        return await self.transcribe_audio(audio_data, **kwargs)

    async def detect_language(
        self, audio: str | np.ndarray | io.BytesIO | io.BufferedReader, **kwargs: Any
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

    async def stream_transcribe(
        self,
        audio_source: AsyncIterator[bytes | np.ndarray],
        language: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[TranscriptionChunk]:
        """
        Stream-transcribe audio from an async iterator of audio chunks.

        Default implementation collects all chunks, runs a single transcribe,
        and yields one final TranscriptionChunk. Providers can override for
        true incremental output.

        Args:
            audio_source: Async iterator yielding raw bytes or numpy arrays
            language: Language code hint
            **kwargs: Provider-specific parameters

        Yields:
            TranscriptionChunk with partial or final transcription text
        """
        chunks: list[np.ndarray] = []
        async for chunk in audio_source:
            if isinstance(chunk, bytes):
                arr: np.ndarray = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                arr = chunk
            chunks.append(arr)

        if not chunks:
            return

        audio = np.concatenate(chunks)
        result = await self.transcribe_audio(audio, language=language, **kwargs)
        text: str = result.get("text", "") if isinstance(result, dict) else str(result)
        yield TranscriptionChunk(text=text, is_final=True, language=language or "unknown")
