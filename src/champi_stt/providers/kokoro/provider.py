"""Kokoro local STT provider.

Kokoro (https://github.com/hexgrad/kokoro) is a lightweight, fully-offline
speech model.  Install the optional extra before use::

    pip install "champi-stt[kokoro]"

The provider calls ``KPipeline.recognize()`` to convert raw audio to text and
returns a standard :class:`~champi_stt.core.response.TranscriptionResponse`.
"""

import asyncio
import io
import time
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from champi_stt.core.base_provider import BaseSTTProvider
from champi_stt.core.response import TranscriptionResponse
from champi_stt.providers.kokoro.config import KokoroConfig
from champi_stt.providers.kokoro.exceptions import (
    KokoroNotInstalledError,
    KokoroTranscriptionError,
)

try:
    from kokoro import KPipeline

    KOKORO_AVAILABLE = True
except ImportError:
    KPipeline = None  # type: ignore[assignment,misc]
    KOKORO_AVAILABLE = False

try:
    import soundfile as sf

    SOUNDFILE_AVAILABLE = True
except ImportError:
    sf = None  # type: ignore[assignment]
    SOUNDFILE_AVAILABLE = False


class KokoroSTTProvider(BaseSTTProvider):
    """Local STT provider backed by the Kokoro speech model.

    Kokoro runs entirely offline; no API key or network connection is required
    after the initial package install.
    """

    name = "Kokoro"

    def __init__(self, config: KokoroConfig) -> None:
        super().__init__(config)
        self.config: KokoroConfig = config
        self._pipeline: Any = None

    # ------------------------------------------------------------------
    # Lifecycle

    async def initialize(self) -> None:
        """Load the Kokoro pipeline.

        Raises:
            KokoroNotInstalledError: If the ``kokoro`` package is not installed.
        """
        if self._initialized:
            return

        if not KOKORO_AVAILABLE:
            raise KokoroNotInstalledError(
                "The kokoro package is required for KokoroSTTProvider. "
                "Install it with: pip install 'champi-stt[kokoro]'"
            )

        loop = asyncio.get_running_loop()
        self._pipeline = await loop.run_in_executor(
            None,
            lambda: KPipeline(
                lang_code=self.config.lang_code,
                device=self.config.device,
                repo_id=self.config.model_id,
            ),
        )
        self._initialized = True
        logger.info(
            "Kokoro provider initialized (model={}, device={})",
            self.config.model_id,
            self.config.device,
        )

    async def shutdown(self) -> None:
        """Release the Kokoro pipeline and free resources."""
        self._pipeline = None
        self._initialized = False
        logger.info("Kokoro provider shut down")

    # ------------------------------------------------------------------
    # Properties

    @property
    def is_loaded(self) -> bool:
        """``True`` when the pipeline is ready to transcribe."""
        return self._initialized

    @property
    def is_initialized(self) -> bool:
        """``True`` when the pipeline is ready to transcribe."""
        return self._initialized

    # ------------------------------------------------------------------
    # Transcription

    async def transcribe(
        self,
        audio_data: bytes | np.ndarray | str | Path,
        language: str | None = None,
        **kwargs: Any,
    ) -> TranscriptionResponse:
        """Transcribe audio using the local Kokoro pipeline.

        Args:
            audio_data: Audio as raw bytes, a NumPy array (float32 or int16),
                        or a file path (str / Path).
            language:   Language hint forwarded to the pipeline.  When ``None``
                        the language code from :attr:`config` is used.
            **kwargs:   Reserved for future provider-specific options.

        Returns:
            :class:`~champi_stt.core.response.TranscriptionResponse`

        Raises:
            RuntimeError:            If the provider has not been initialized.
            KokoroTranscriptionError: If the Kokoro pipeline raises an error.
        """
        if not self._initialized:
            raise RuntimeError("Provider not initialized — call initialize() first")

        wav_bytes = await self._to_wav_bytes(audio_data)
        lang = language or self.config.lang_code

        start = time.perf_counter()
        loop = asyncio.get_running_loop()
        try:
            text = await loop.run_in_executor(
                None, self._run_recognize, wav_bytes, lang
            )
        except Exception as exc:
            raise KokoroTranscriptionError(
                f"Kokoro transcription failed: {exc}"
            ) from exc

        processing_time = time.perf_counter() - start
        return TranscriptionResponse(
            text=text.strip(),
            language=lang,
            processing_time=processing_time,
        )

    # ------------------------------------------------------------------
    # Context-manager support

    async def __aenter__(self) -> "KokoroSTTProvider":
        await self.initialize()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.shutdown()

    # ------------------------------------------------------------------
    # Model info

    async def get_model_info(self) -> dict[str, Any]:
        """Return provider metadata."""
        return {
            "status": "loaded" if self._initialized else "not_initialized",
            "provider": "kokoro",
            "model_id": self.config.model_id,
            "device": self.config.device,
            "lang_code": self.config.lang_code,
        }

    # ------------------------------------------------------------------
    # Internal helpers

    def _run_recognize(self, wav_bytes: bytes, lang: str) -> str:
        """Synchronous call into the Kokoro pipeline (runs in a thread pool)."""
        return self._pipeline.recognize(wav_bytes, lang=lang)  # type: ignore[union-attr]

    async def _to_wav_bytes(self, audio: bytes | np.ndarray | str | Path) -> bytes:
        """Convert any supported audio input to WAV bytes."""
        if isinstance(audio, Path):
            audio = str(audio)

        if isinstance(audio, str):
            return Path(audio).read_bytes()

        if isinstance(audio, bytes):
            return audio

        if isinstance(audio, np.ndarray):
            if not SOUNDFILE_AVAILABLE:
                raise ImportError(
                    "soundfile is required for NumPy array input. "
                    "Install with: pip install soundfile"
                )
            buf = io.BytesIO()
            if np.issubdtype(audio.dtype, np.floating):
                data = (audio * 32767).clip(-32768, 32767).astype(np.int16)
            else:
                data = audio.astype(np.int16)
            sf.write(
                buf,
                data,
                samplerate=self.config.sample_rate,
                format="WAV",
                subtype="PCM_16",
            )
            return buf.getvalue()

        raise TypeError(f"Unsupported audio type: {type(audio)}")
