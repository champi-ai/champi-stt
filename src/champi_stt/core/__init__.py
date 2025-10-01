"""
Core abstractions for champi-stt multi-provider support
"""

from champi_stt.core.base_config import BaseSTTConfig
from champi_stt.core.base_provider import BaseSTTProvider
from champi_stt.core.base_transcriber import BaseTranscriber
from champi_stt.core.base_model_manager import BaseModelManager

__all__ = [
    "BaseSTTConfig",
    "BaseSTTProvider",
    "BaseTranscriber",
    "BaseModelManager",
]
