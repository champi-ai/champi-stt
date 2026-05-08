"""Diarization configuration."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class DiarizationConfig:
    """Configuration for speaker diarization.

    Attributes:
        hf_token:          HuggingFace access token for pyannote models.
        num_speakers:      Expected number of speakers (None = auto-detect).
        min_speakers:      Minimum number of speakers when auto-detecting.
        max_speakers:      Maximum number of speakers when auto-detecting.
        model:             pyannote pipeline model identifier.
        device:            Compute device ("cpu", "cuda", "mps").
    """

    hf_token: str | None = None
    num_speakers: int | None = None
    min_speakers: int | None = None
    max_speakers: int | None = None
    model: str = "pyannote/speaker-diarization-3.1"
    device: str = "cpu"

    @classmethod
    def from_env(cls) -> "DiarizationConfig":
        import os

        return cls(hf_token=os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN"))
