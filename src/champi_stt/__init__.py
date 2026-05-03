"""
Champi STT - Multi-Provider Speech-to-Text Library
===================================================

A modular, extensible STT library supporting multiple providers:
- WhisperLive (local faster-whisper backend)
- OpenAI (coming soon)
- Deepgram (coming soon)

Quick Start:
-----------
```python
from champi_stt import get_provider

# Get default provider (WhisperLive)
provider = get_provider()
await provider.initialize()

# Transcribe audio
result = await provider.transcribe("audio.wav")
print(result["text"])
```

Provider-Specific Usage:
-----------------------
```python
from champi_stt import get_provider
from champi_stt.providers.whisperlive import WhisperLiveConfig

# Custom WhisperLive config
config = WhisperLiveConfig(model_size="base", device="cpu")
provider = get_provider("whisperlive", config=config)
```
"""

# Factory functions (primary API)
from champi_stt.factory import (
    get_provider,
    get_default_provider,
    list_providers,
)

# Base classes (for type hints and custom providers)
from champi_stt.core.base_provider import BaseSTTProvider
from champi_stt.core.base_config import BaseSTTConfig
from champi_stt.core.base_transcriber import BaseTranscriber
from champi_stt.core.base_model_manager import BaseModelManager

# Backwards compatibility: expose WhisperLive directly
from champi_stt.providers.whisperlive import (
    WhisperLiveConfig,
    WhisperLiveSTTProvider,
    WhisperLiveTranscriber,
)

__version__ = "0.0.1"

__all__ = [
    # Factory functions (recommended API)
    "get_provider",
    "get_default_provider",
    "list_providers",

    # Base classes
    "BaseSTTProvider",
    "BaseSTTConfig",
    "BaseTranscriber",
    "BaseModelManager",

    # Backwards compatibility
    "WhisperLiveConfig",
    "WhisperLiveSTTProvider",
    "WhisperLiveTranscriber",

    # Version
    "__version__",
]
