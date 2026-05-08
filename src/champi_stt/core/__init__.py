"""
Core abstractions for champi-stt multi-provider support
"""

from champi_stt.core.base_config import BaseSTTConfig
from champi_stt.core.base_model_manager import BaseModelManager
from champi_stt.core.base_provider import BaseSTTProvider
from champi_stt.core.base_transcriber import BaseTranscriber
from champi_stt.core.response import TranscriptionChunk
from champi_stt.core.streaming import StreamingTranscriptionConfig

__all__ = [
    "BaseModelManager",
    "BaseSTTConfig",
    "BaseSTTProvider",
    "BaseTranscriber",
    "StreamingTranscriptionConfig",
    "TranscriptionChunk",
]
