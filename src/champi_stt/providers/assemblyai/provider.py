"""
AssemblyAI real-time streaming STT provider.

Uses the AssemblyAI WebSocket API for low-latency streaming transcription.
Implements both one-shot transcription (via file upload REST API) and
streaming transcription (via WebSocket).
"""

import asyncio
import io
import json
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from champi_stt.core.base_provider import BaseSTTProvider
from champi_stt.core.response import TranscriptionResponse, TranscriptionSegment
from champi_stt.providers.assemblyai.config import AssemblyAIConfig
from champi_stt.providers.assemblyai.exceptions import (
    AssemblyAIAuthError,
    AssemblyAIConnectionError,
    AssemblyAIStreamingError,
)

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    HTTPX_AVAILABLE = False

try:
    import websockets

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    websockets = None  # type: ignore[assignment]
    WEBSOCKETS_AVAILABLE = False

try:
    import soundfile as sf

    SOUNDFILE_AVAILABLE = True
except ImportError:
    sf = None  # type: ignore[assignment]
    SOUNDFILE_AVAILABLE = False

_REST_BASE = "https://api.assemblyai.com/v2"
_WS_URL = "wss://api.assemblyai.com/v2/realtime/ws"


class AssemblyAIProvider(BaseSTTProvider):
    """
    AssemblyAI STT provider supporting both batch and real-time streaming.

    Batch mode:   upload audio → poll for transcript → return result
    Streaming:    open WebSocket → stream PCM chunks → yield partial results
    """

    name = "AssemblyAI"

    def __init__(self, config: AssemblyAIConfig) -> None:
        super().__init__(config)
        self.config: AssemblyAIConfig = config
        self._http: Any = None

    async def initialize(self) -> None:
        if self._initialized:
            return

        if not self.config.api_key:
            raise AssemblyAIAuthError(
                "AssemblyAI API key is required. Set ASSEMBLYAI_API_KEY or pass api_key in config."
            )

        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for AssemblyAIProvider. Install with: pip install httpx"
            )

        self._http = httpx.AsyncClient(
            headers={"authorization": self.config.api_key},
            timeout=120.0,
        )
        self._initialized = True
        logger.info("AssemblyAI provider initialized")

    async def shutdown(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None
        self._initialized = False
        logger.info("AssemblyAI provider shut down")

    @property
    def is_loaded(self) -> bool:
        return self._initialized

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def transcribe(
        self,
        audio_data: bytes | np.ndarray | str,
        language: str | None = None,
        **kwargs: Any,
    ) -> TranscriptionResponse:
        if not self._initialized:
            raise RuntimeError("Provider not initialized. Call initialize() first.")

        start = time.perf_counter()

        audio_bytes = await self._to_bytes(audio_data)
        upload_url = await self._upload(audio_bytes)
        result = await self._submit_and_poll(upload_url, language=language)

        processing_time = time.perf_counter() - start
        return self._parse_response(result, processing_time)

    async def stream_transcribe(
        self,
        audio_source: AsyncIterator[np.ndarray],
        language: str | None = None,
    ) -> AsyncIterator[TranscriptionResponse]:
        """
        Stream audio chunks through the AssemblyAI real-time WebSocket API.

        Args:
            audio_source: Async iterator yielding int16 numpy audio chunks
            language:     Language code (AssemblyAI auto-detects if None)

        Yields:
            TranscriptionResponse for each final transcript received
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets is required for streaming. Install with: pip install websockets"
            )
        if not self._initialized:
            raise RuntimeError("Provider not initialized. Call initialize() first.")

        params = f"sample_rate={self.config.sample_rate}"
        if language:
            params += f"&language_code={language}"
        if self.config.word_boost:
            params += f"&word_boost={json.dumps(self.config.word_boost)}"
        if self.config.disable_partial_transcripts:
            params += "&disable_partial_transcripts=true"
        params += f"&end_utterance_silence_threshold={self.config.end_utterance_silence_threshold}"

        url = f"{_WS_URL}?{params}"
        headers = {"Authorization": self.config.api_key}

        try:
            async with websockets.connect(url, additional_headers=headers) as ws:
                # Confirm session
                session_msg = json.loads(await ws.recv())
                if session_msg.get("error"):
                    raise AssemblyAIAuthError(session_msg["error"])
                logger.debug(f"AssemblyAI session opened: {session_msg.get('session_id')}")

                async def _send() -> None:
                    async for chunk in audio_source:
                        pcm = self._to_int16_bytes(chunk)
                        await ws.send(pcm)
                    # Signal end of stream
                    await ws.send(json.dumps({"terminate_session": True}))

                send_task = asyncio.create_task(_send())

                try:
                    async for raw in ws:
                        msg = json.loads(raw)

                        if msg.get("error"):
                            raise AssemblyAIStreamingError(msg["error"])

                        if msg.get("message_type") == "FinalTranscript":
                            text = msg.get("text", "").strip()
                            if text:
                                yield TranscriptionResponse(
                                    text=text,
                                    language=msg.get("language_code", "unknown"),
                                    duration=msg.get("audio_duration", 0.0),
                                )
                finally:
                    send_task.cancel()

        except (OSError, Exception) as exc:
            if "websockets" in type(exc).__module__:
                raise AssemblyAIConnectionError(f"WebSocket error: {exc}") from exc
            raise

    # ------------------------------------------------------------------ helpers

    async def _upload(self, audio_bytes: bytes) -> str:
        """Upload raw audio to AssemblyAI and return the upload URL."""
        response = await self._http.post(
            f"{_REST_BASE}/upload",
            content=audio_bytes,
            headers={"content-type": "application/octet-stream"},
        )
        response.raise_for_status()
        return response.json()["upload_url"]

    async def _submit_and_poll(
        self, upload_url: str, language: str | None = None
    ) -> dict[str, Any]:
        """Submit a transcription job and poll until complete."""
        payload: dict[str, Any] = {"audio_url": upload_url}
        if language:
            payload["language_code"] = language

        submit = await self._http.post(f"{_REST_BASE}/transcript", json=payload)
        submit.raise_for_status()
        transcript_id = submit.json()["id"]
        logger.debug(f"AssemblyAI transcript submitted: {transcript_id}")

        poll_url = f"{_REST_BASE}/transcript/{transcript_id}"
        while True:
            await asyncio.sleep(1.0)
            resp = await self._http.get(poll_url)
            resp.raise_for_status()
            data = resp.json()
            status = data["status"]

            if status == "completed":
                return data
            if status == "error":
                raise AssemblyAIStreamingError(
                    f"Transcription failed: {data.get('error', 'unknown error')}"
                )

    def _parse_response(
        self, data: dict[str, Any], processing_time: float = 0.0
    ) -> TranscriptionResponse:
        words = data.get("words") or []
        segments = [
            TranscriptionSegment(
                id=i,
                start=w.get("start", 0) / 1000.0,
                end=w.get("end", 0) / 1000.0,
                text=w.get("text", ""),
            )
            for i, w in enumerate(words)
        ]
        return TranscriptionResponse(
            text=data.get("text") or "",
            language=data.get("language_code") or "unknown",
            duration=data.get("audio_duration") or 0.0,
            language_probability=data.get("language_confidence") or 0.0,
            segments=segments,
            processing_time=processing_time,
        )

    async def _to_bytes(self, audio: bytes | np.ndarray | str) -> bytes:
        if isinstance(audio, bytes):
            return audio
        if isinstance(audio, (str, Path)):
            return Path(audio).read_bytes()
        if isinstance(audio, np.ndarray):
            if not SOUNDFILE_AVAILABLE:
                raise ImportError("soundfile required for numpy input. Install with: pip install soundfile")
            buf = io.BytesIO()
            sf.write(buf, audio, self.config.sample_rate, format="WAV", subtype="PCM_16")
            return buf.getvalue()
        raise TypeError(f"Unsupported audio type: {type(audio)}")

    @staticmethod
    def _to_int16_bytes(audio: np.ndarray) -> bytes:
        if audio.dtype in (np.float32, np.float64):
            audio = (audio * 32767).clip(-32768, 32767).astype(np.int16)
        elif audio.dtype != np.int16:
            audio = audio.astype(np.int16)
        return audio.tobytes()

    async def __aenter__(self) -> "AssemblyAIProvider":
        await self.initialize()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.shutdown()
