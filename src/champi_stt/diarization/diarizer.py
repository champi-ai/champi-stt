"""Speaker diarization via pyannote.audio."""

from __future__ import annotations

import dataclasses
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

try:
    from pyannote.audio import Pipeline  # type: ignore[import-untyped]

    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False

    class Pipeline:  # type: ignore[no-redef]
        pass


from champi_stt.diarization.config import DiarizationConfig


@dataclasses.dataclass
class DiarizationSegment:
    """A time-stamped segment attributed to a speaker.

    Attributes:
        speaker_id: Speaker label (e.g. "SPEAKER_00").
        start:      Segment start time in seconds.
        end:        Segment end time in seconds.
        text:       Transcription text for this segment (empty until annotated).
    """

    speaker_id: str
    start: float
    end: float
    text: str = ""


class Diarizer:
    """Wraps a pyannote.audio pipeline to label audio with speaker segments."""

    def __init__(self, config: DiarizationConfig | None = None) -> None:
        self.config = config or DiarizationConfig()
        self._pipeline: Pipeline | None = None

    async def initialize(self) -> None:
        """Load the pyannote diarization pipeline."""
        if not PYANNOTE_AVAILABLE:
            raise ImportError(
                "pyannote.audio is required for diarization. "
                "Install with: pip install 'champi-stt[diarization]'"
            )
        import asyncio

        def _load() -> Pipeline:
            kwargs: dict[str, Any] = {}
            if self.config.hf_token:
                kwargs["use_auth_token"] = self.config.hf_token
            return Pipeline.from_pretrained(self.config.model, **kwargs)

        self._pipeline = await asyncio.get_running_loop().run_in_executor(None, _load)
        logger.info(f"Diarization pipeline loaded: {self.config.model}")

    async def diarize(
        self,
        audio: np.ndarray | bytes | str | Path,
        sample_rate: int = 16000,
    ) -> list[DiarizationSegment]:
        """Run diarization on audio and return speaker-labelled segments.

        Args:
            audio:       Audio as numpy array (float32), raw bytes (int16 PCM),
                         or a file path.
            sample_rate: Sample rate of the audio in Hz.

        Returns:
            List of DiarizationSegment sorted by start time.
        """
        if self._pipeline is None:
            raise RuntimeError("Call initialize() before diarize()")

        import asyncio

        audio_path = await asyncio.get_running_loop().run_in_executor(
            None, lambda: self._to_wav_path(audio, sample_rate)
        )

        diarize_kwargs: dict[str, Any] = {}
        if self.config.num_speakers is not None:
            diarize_kwargs["num_speakers"] = self.config.num_speakers
        else:
            if self.config.min_speakers is not None:
                diarize_kwargs["min_speakers"] = self.config.min_speakers
            if self.config.max_speakers is not None:
                diarize_kwargs["max_speakers"] = self.config.max_speakers

        def _run() -> Any:
            return self._pipeline(audio_path, **diarize_kwargs)

        annotation = await asyncio.get_running_loop().run_in_executor(None, _run)

        segments: list[DiarizationSegment] = []
        for turn, _, speaker in annotation.itertracks(yield_label=True):
            segments.append(
                DiarizationSegment(
                    speaker_id=speaker,
                    start=round(turn.start, 3),
                    end=round(turn.end, 3),
                )
            )

        return sorted(segments, key=lambda s: s.start)

    def annotate_transcription(
        self,
        segments: list[DiarizationSegment],
        text: str,
    ) -> list[DiarizationSegment]:
        """Attach transcription text to the closest diarization segment.

        This is a simple heuristic: split text by sentence-ending punctuation
        and assign each part to the next available segment in order.

        Args:
            segments: Diarization segments from diarize().
            text:     Full transcription text.

        Returns:
            Segments with the text field populated.
        """
        import re

        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
        for i, part in enumerate(parts):
            if i < len(segments):
                segments[i].text = part
        return segments

    @staticmethod
    def _to_wav_path(
        audio: np.ndarray | bytes | str | Path,
        sample_rate: int,
    ) -> str:
        """Convert audio to a temporary WAV file and return its path."""
        if isinstance(audio, str | Path):
            return str(audio)

        import soundfile as sf  # type: ignore[import-untyped]

        if isinstance(audio, bytes):
            arr: np.ndarray = (
                np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            )
        else:
            arr = audio

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, arr, sample_rate)
            return tmp.name

    async def shutdown(self) -> None:
        """Release the pipeline."""
        self._pipeline = None
