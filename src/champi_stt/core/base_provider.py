"""
Base STT provider interface
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

import numpy as np

from champi_stt.core.base_config import BaseSTTConfig
from champi_stt.core.response import TranscriptionChunk


class BaseSTTProvider(ABC):
    """
    Abstract base class for all STT providers.

    All providers (WhisperLive, OpenAI, Deepgram, etc.) must implement this interface.
    """

    def __init__(self, config: BaseSTTConfig):
        self.config = config
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the provider.

        This may include:
        - Loading models (for local providers)
        - Validating API keys (for cloud providers)
        - Setting up connections
        - Validating directories
        """
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes | np.ndarray | str,
        language: str | None = None,
        prompt: str | None = None,
        response_format: str = "json",
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str | dict[str, Any]:
        """
        Transcribe audio data.

        Args:
            audio_data: Audio data (bytes, numpy array, or file path)
            language: Language code for transcription (overrides config)
            prompt: Initial prompt/context for the model
            response_format: Output format ("json", "text", "verbose_json")
            temperature: Sampling temperature (0.0 = deterministic)
            **kwargs: Provider-specific parameters

        Returns:
            Transcription result (format depends on response_format)
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown the provider and clean up resources.

        This may include:
        - Unloading models
        - Closing connections
        - Clearing caches
        """
        pass

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if provider is initialized and ready"""
        pass

    # Optional methods (providers can override)

    async def translate(
        self,
        audio_data: bytes | np.ndarray | str,
        prompt: str | None = None,
        response_format: str = "json",
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str | dict[str, Any]:
        """
        Translate audio to English.

        Default implementation calls transcribe with task="translate".
        Providers can override for custom logic.
        """
        return await self.transcribe(
            audio_data,
            language=None,  # Auto-detect
            prompt=prompt,
            response_format=response_format,
            temperature=temperature,
            task="translate",
            **kwargs,
        )

    async def stream_transcribe(
        self,
        audio_source: AsyncIterator[bytes | np.ndarray],
        language: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[TranscriptionChunk]:
        """
        Stream-transcribe audio from an async iterator of audio chunks.

        Default implementation collects all audio, transcribes once, and
        yields a single final TranscriptionChunk. Providers can override
        for true incremental/real-time output.

        Args:
            audio_source: Async iterator of raw bytes or float32 numpy arrays
            language: Language code hint
            **kwargs: Provider-specific parameters

        Yields:
            TranscriptionChunk with partial or final text
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
        result = await self.transcribe(audio, language=language, **kwargs)
        text = result if isinstance(result, str) else str(result.get("text", "") if isinstance(result, dict) else result)
        yield TranscriptionChunk(text=text, is_final=True, language=language or "unknown")

    async def detect_language(
        self, audio_data: bytes | np.ndarray | str, **kwargs: Any
    ) -> tuple[str, float, list[tuple[str, float]]]:
        """
        Detect language of audio.

        Returns:
            Tuple of (language_code, probability, all_language_probabilities)

        Default implementation returns ("en", 1.0, []).
        Providers should override if they support language detection.
        """
        return ("en", 1.0, [])

    async def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the loaded model/provider.

        Default implementation returns basic status.
        Providers can override for detailed info.
        """
        return {
            "status": "loaded" if self._initialized else "not_initialized",
            "provider": self.__class__.__name__,
        }

    async def save_transcription(
        self, text: str, prefix: str = "stt", metadata: dict | None = None
    ) -> str | None:
        """
        Save transcription to file.

        Returns:
            Path to saved file or None if saving disabled
        """
        import asyncio
        from datetime import datetime
        from pathlib import Path

        if not self.config.save_transcriptions:
            return None

        # Ensure directory exists
        trans_dir = Path(self.config.transcriptions_dir)
        await asyncio.get_running_loop().run_in_executor(
            None, lambda: trans_dir.mkdir(parents=True, exist_ok=True)
        )

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{prefix}_{timestamp}.txt"
        filepath = trans_dir / filename

        # Build content
        content = []
        if metadata:
            content.extend(
                [
                    "=" * 50,
                    "TRANSCRIPTION METADATA",
                    "=" * 50,
                ]
            )
            for key, value in metadata.items():
                content.append(f"{key}: {value}")
            content.extend(["=" * 50, ""])

        content.append(text)

        # Write file
        file_content = "\n".join(content)
        await asyncio.get_running_loop().run_in_executor(
            None, lambda: filepath.write_text(file_content, encoding="utf-8")
        )

        return str(filepath)
