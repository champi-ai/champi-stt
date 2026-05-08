"""Deepgram REST API STT provider."""

import io
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from champi_stt.core.response import TranscriptionResponse, TranscriptionSegment
from champi_stt.providers.deepgram.config import DeepgramConfig
from champi_stt.providers.deepgram.exceptions import (
    DeepgramAPIError,
    DeepgramAuthError,
)

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    HTTPX_AVAILABLE = False

try:
    import soundfile as sf

    SOUNDFILE_AVAILABLE = True
except ImportError:
    sf = None  # type: ignore[assignment]
    SOUNDFILE_AVAILABLE = False

_DEEPGRAM_LISTEN_URL = "{base_url}/listen"


class DeepgramProvider:
    """STT provider backed by the Deepgram REST API (Nova-2 / Whisper tiers)."""

    def __init__(self, config: DeepgramConfig | None = None):
        self.config = config or DeepgramConfig.from_env()
        self.name = "Deepgram"
        self._initialized = False
        self._http: Any = None

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def is_loaded(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        if self._initialized:
            return

        if not HTTPX_AVAILABLE:
            raise ImportError("httpx is required: pip install httpx")

        if not self.config.api_key:
            raise DeepgramAuthError(
                "Deepgram API key not set. Pass api_key= or set DEEPGRAM_API_KEY."
            )

        self._http = httpx.AsyncClient(
            headers={"Authorization": f"Token {self.config.api_key}"},
            timeout=self.config.timeout_seconds,
        )
        self._initialized = True
        logger.debug("Deepgram provider initialized")

    async def shutdown(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None
        self._initialized = False
        logger.debug("Deepgram provider shut down")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()

    async def transcribe(
        self,
        audio_data: bytes | np.ndarray | str | Path,
        language: str | None = None,
        **kwargs,
    ) -> TranscriptionResponse:
        """
        Transcribe audio using the Deepgram REST API.

        Args:
            audio_data: Audio as bytes, numpy array, file path string, or Path
            language: BCP-47 language code (uses config default if None)

        Returns:
            TranscriptionResponse
        """
        if not self._initialized:
            raise RuntimeError("Provider not initialized — call initialize() first")

        temp_path: str | None = None
        try:
            audio_bytes, temp_path = await self._prepare_audio(audio_data)
            return await self._call_api(
                audio_bytes,
                language=language or self.config.language,
            )
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    async def _prepare_audio(
        self, audio_data: bytes | np.ndarray | str | Path
    ) -> tuple[bytes, str | None]:
        """Convert input to raw bytes. Returns (bytes, temp_path_or_None)."""
        if isinstance(audio_data, Path):
            audio_data = str(audio_data)

        if isinstance(audio_data, str):
            with open(audio_data, "rb") as f:
                return f.read(), None

        if isinstance(audio_data, np.ndarray):
            if not SOUNDFILE_AVAILABLE:
                raise ImportError("soundfile is required for numpy array input")
            buf = io.BytesIO()
            if np.issubdtype(audio_data.dtype, np.floating):
                data = (audio_data * 32767).clip(-32768, 32767).astype(np.int16)
            else:
                data = audio_data
            sf.write(buf, data, samplerate=16000, format="WAV", subtype="PCM_16")
            return buf.getvalue(), None

        return audio_data, None

    async def _call_api(
        self, audio_bytes: bytes, language: str | None
    ) -> TranscriptionResponse:
        url = _DEEPGRAM_LISTEN_URL.format(base_url=self.config.base_url)

        params: dict[str, Any] = {
            "model": self.config.model,
            "smart_format": str(self.config.smart_format).lower(),
            "punctuate": str(self.config.punctuate).lower(),
            "utterances": str(self.config.utterances).lower(),
            "diarize": str(self.config.diarize).lower(),
        }
        if language:
            params["language"] = language

        try:
            resp = await self._http.post(
                url,
                content=audio_bytes,
                headers={"Content-Type": "audio/wav"},
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise DeepgramAPIError(f"Deepgram API call failed: {e}") from e

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> TranscriptionResponse:
        try:
            result = data["results"]["channels"][0]["alternatives"][0]
        except (KeyError, IndexError) as e:
            raise DeepgramAPIError(f"Unexpected response format: {e}") from e

        text = result.get("transcript", "").strip()
        words = result.get("words", [])
        confidence = result.get("confidence", 0.0)

        metadata = data.get("metadata", {})
        duration = metadata.get("duration", 0.0)
        detected_language = (
            data.get("results", {})
            .get("channels", [{}])[0]
            .get("detected_language", "unknown")
        )

        segments = []
        if words:
            segments.append(
                TranscriptionSegment(
                    id=0,
                    start=words[0].get("start", 0.0) if words else 0.0,
                    end=words[-1].get("end", duration) if words else duration,
                    text=text,
                    avg_logprob=confidence - 1.0,
                )
            )

        return TranscriptionResponse(
            text=text,
            language=detected_language,
            duration=duration,
            segments=segments,
        )

    async def get_model_info(self) -> dict[str, Any]:
        return {
            "status": "loaded" if self._initialized else "not_initialized",
            "provider": "deepgram",
            "model": self.config.model,
        }
