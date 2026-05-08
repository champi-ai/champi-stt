"""Streaming transcription configuration and helpers."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class StreamingTranscriptionConfig:
    """Configuration for real-time streaming transcription.

    Attributes:
        chunk_size:        Number of audio frames per chunk sent to the provider.
        overlap_frames:    Frames of overlap between consecutive chunks for context.
        vad_aggressiveness: WebRTC VAD mode (0=least, 3=most aggressive).
        language:          Language hint forwarded to the provider (None = auto).
        sample_rate:       Audio sample rate in Hz.
    """

    chunk_size: int = 4096
    overlap_frames: int = 512
    vad_aggressiveness: int = 2
    language: str | None = None
    sample_rate: int = 16000

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if self.overlap_frames < 0:
            raise ValueError("overlap_frames must be >= 0")
        if self.vad_aggressiveness not in (0, 1, 2, 3):
            raise ValueError("vad_aggressiveness must be 0, 1, 2, or 3")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be > 0")
