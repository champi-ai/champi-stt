"""Speaker diarization for champi-stt."""

from champi_stt.diarization.config import DiarizationConfig
from champi_stt.diarization.diarizer import DiarizationSegment, Diarizer

__all__ = ["DiarizationConfig", "DiarizationSegment", "Diarizer"]
