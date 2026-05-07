"""
Core abstractions for champi-stt multi-provider support
"""

from champi_stt.core.base_config import BaseSTTConfig
from champi_stt.core.base_model_manager import BaseModelManager
from champi_stt.core.base_provider import BaseSTTProvider
from champi_stt.core.base_transcriber import BaseTranscriber

__all__ = [
    "BaseModelManager",
    "BaseSTTConfig",
    "BaseSTTProvider",
    "BaseTranscriber",
]
