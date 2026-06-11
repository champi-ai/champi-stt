"""OpenAI Whisper API STT provider."""

import io
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from champi_stt.core.response import TranscriptionResponse, TranscriptionSegment
from champi_stt.providers.openai_whisper.config import OpenAIWhisperConfig
from champi_stt.providers.openai_whisper.exceptions import (
    OpenAIWhisperAPIError,
    OpenAIWhisperAuthError,
    OpenAIWhisperFileSizeError,
)

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    openai = None  # type: ignore[assignment]
    OPENAI_AVAILABLE = False

try:
    import soundfile as sf

    SOUNDFILE_AVAILABLE = True
except ImportError:
    sf = None  # type: ignore[assignment]
    SOUNDFILE_AVAILABLE = False


class OpenAIWhisperProvider:
    """STT provider backed by the OpenAI Whisper transcription API."""

    def __init__(self, config: OpenAIWhisperConfig | None = None):
        self.config = config or OpenAIWhisperConfig.from_env()
        self.name = "OpenAI Whisper"
        self._initialized = False
        self._client: Any = None

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def is_loaded(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        if self._initialized:
            return

        if not OPENAI_AVAILABLE:
            raise ImportError("openai package is required: pip install openai")

        if not self.config.api_key:
            raise OpenAIWhisperAuthError(
                "OpenAI API key not set. Pass api_key= or set OPENAI_API_KEY."
            )

        kwargs: dict[str, Any] = {"api_key": self.config.api_key}
        if self.config.base_url:
            kwargs["base_url"] = self.config.base_url
        if self.config.extra_headers:
            kwargs["default_headers"] = self.config.extra_headers

        self._client = openai.AsyncOpenAI(**kwargs)
        self._initialized = True
        logger.debug("OpenAI Whisper provider initialized")

    async def shutdown(self) -> None:
        self._client = None
        self._initialized = False
        logger.debug("OpenAI Whisper provider shut down")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()

    async def transcribe(
        self,
        audio_data: bytes | np.ndarray | str | Path,
        language: str | None = None,
        prompt: str | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> TranscriptionResponse:
        """
        Transcribe audio using the OpenAI Whisper API.

        Args:
            audio_data: Audio as bytes, numpy array, file path string, or Path
            language: BCP-47 language code (auto-detect if None)
            prompt: Context hint for the model
            temperature: Sampling temperature (0.0 = deterministic)

        Returns:
            TranscriptionResponse
        """
        if not self._initialized:
            raise RuntimeError("Provider not initialized — call initialize() first")

        temp_path: str | None = None
        try:
            file_obj, temp_path = await self._prepare_audio(audio_data)
            return await self._call_api(
                file_obj,
                language=language or self.config.language,
                prompt=prompt,
                temperature=temperature
                if temperature is not None
                else self.config.temperature,
            )
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    async def _prepare_audio(
        self, audio_data: bytes | np.ndarray | str | Path
    ) -> tuple[Any, str | None]:
        """Convert audio_data to a file-like object. Returns (file_obj, temp_path_or_None)."""
        if isinstance(audio_data, Path):
            audio_data = str(audio_data)

        if isinstance(audio_data, str):
            path = audio_data
            size = os.path.getsize(path)
            if size > self.config.max_file_size_bytes:
                raise OpenAIWhisperFileSizeError(
                    f"File {path} is {size} bytes, exceeds 25 MB limit"
                )
            return open(path, "rb"), None

        if isinstance(audio_data, np.ndarray):
            if not SOUNDFILE_AVAILABLE:
                raise ImportError("soundfile is required for numpy array input")
            buf = io.BytesIO()
            # Normalize float arrays
            if np.issubdtype(audio_data.dtype, np.floating):
                data = (audio_data * 32767).clip(-32768, 32767).astype(np.int16)
            else:
                data = audio_data
            sf.write(buf, data, samplerate=16000, format="WAV", subtype="PCM_16")
            buf.seek(0)
            buf.name = "audio.wav"
            return buf, None

        # bytes
        if len(audio_data) > self.config.max_file_size_bytes:
            raise OpenAIWhisperFileSizeError(
                f"Audio bytes ({len(audio_data)}) exceed 25 MB limit"
            )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp.flush()
            tmp_name = tmp.name
        return open(tmp_name, "rb"), tmp_name

    async def _call_api(
        self,
        file_obj: Any,
        language: str | None,
        prompt: str | None,
        temperature: float,
    ) -> TranscriptionResponse:
        try:
            kwargs: dict[str, Any] = {
                "model": self.config.model,
                "file": file_obj,
                "response_format": "verbose_json",
                "temperature": temperature,
                "timestamp_granularities": ["segment"],
            }
            if language:
                kwargs["language"] = language
            if prompt:
                kwargs["prompt"] = prompt

            response = await self._client.audio.transcriptions.create(**kwargs)
        except Exception as e:
            raise OpenAIWhisperAPIError(f"API call failed: {e}") from e
        finally:
            file_obj.close()

        segments = []
        raw_segments = getattr(response, "segments", None) or []
        for i, seg in enumerate(raw_segments):
            segments.append(
                TranscriptionSegment(
                    id=i,
                    start=getattr(seg, "start", 0.0),
                    end=getattr(seg, "end", 0.0),
                    text=getattr(seg, "text", "").strip(),
                    avg_logprob=getattr(seg, "avg_logprob", 0.0),
                    no_speech_prob=getattr(seg, "no_speech_prob", 0.0),
                    tokens=getattr(seg, "tokens", []),
                    temperature=getattr(seg, "temperature", temperature),
                    compression_ratio=getattr(seg, "compression_ratio", 0.0),
                )
            )

        return TranscriptionResponse(
            text=(getattr(response, "text", "") or "").strip(),
            language=getattr(response, "language", "unknown") or "unknown",
            duration=getattr(response, "duration", 0.0) or 0.0,
            segments=segments,
        )

    async def get_model_info(self) -> dict[str, Any]:
        return {
            "status": "loaded" if self._initialized else "not_initialized",
            "provider": "openai_whisper",
            "model": self.config.model,
        }
