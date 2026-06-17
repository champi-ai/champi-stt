"""
Champi STT - Multi-Provider Speech-to-Text Library
===================================================

Stable public API (semver guaranteed from v1.0):

  Factory
  -------
  get_provider(provider_type, config, **kwargs) -> BaseSTTProvider
  get_default_provider() -> BaseSTTProvider
  list_providers() -> list[str]

  Base classes (for type hints and custom provider implementations)
  ----------------------------------------------------------------
  BaseSTTProvider
  BaseSTTConfig
  BaseTranscriber
  BaseModelManager

  Streaming
  ---------
  StreamingTranscriptionConfig
  TranscriptionChunk

  Multi-room audio
  ----------------
  MultiRoomAudioManager
  RoomConfig
  RoomAudioChunk

  Response types
  --------------
  TranscriptionResponse
  TranscriptionSegment

  Diarization
  -----------
  DiarizationConfig
  DiarizationSegment
  Diarizer

Provisional (may change in a minor release with a deprecation warning)
----------------------------------------------------------------------
  WhisperLiveConfig, WhisperLiveSTTProvider, WhisperLiveTranscriber

Internal (no stability guarantee — do not import directly)
----------------------------------------------------------
  Everything under champi_stt.providers.*.*, champi_stt.assistant.*,
  champi_stt.core.audio, champi_stt.core.preprocessing

Deprecation policy
------------------
Symbols will be deprecated for at least one minor release before removal.
Deprecated symbols emit DeprecationWarning on import and are documented in
CHANGELOG.md.

Quick start
-----------
    from champi_stt import get_provider

    provider = get_provider("whisperlive")
    await provider.initialize()
    result = await provider.transcribe("audio.wav")
    print(result)
    await provider.shutdown()
"""

from __future__ import annotations

# Base classes
from champi_stt.core.base_config import BaseSTTConfig
from champi_stt.core.base_model_manager import BaseModelManager
from champi_stt.core.base_provider import BaseSTTProvider
from champi_stt.core.base_transcriber import BaseTranscriber

# Multi-room audio
from champi_stt.core.multi_room import MultiRoomAudioManager, RoomAudioChunk, RoomConfig
from champi_stt.core.response import (
    TranscriptionChunk,
    TranscriptionResponse,
    TranscriptionSegment,
)

# Streaming
from champi_stt.core.streaming import StreamingTranscriptionConfig

# Diarization
from champi_stt.diarization.config import DiarizationConfig
from champi_stt.diarization.diarizer import DiarizationSegment, Diarizer

# Factory (primary entry points)
from champi_stt.factory import get_default_provider, get_provider, list_providers

# Provisional: WhisperLive provider (direct access; stable via get_provider("whisperlive"))
from champi_stt.providers.whisperlive import (
    WhisperLiveConfig,
    WhisperLiveSTTProvider,
    WhisperLiveTranscriber,
)

__version__ = "1.3.1"

__all__ = [
    "BaseModelManager",
    # Base classes — stable
    "BaseSTTConfig",
    "BaseSTTProvider",
    "BaseTranscriber",
    # Diarization — stable
    "DiarizationConfig",
    "DiarizationSegment",
    "Diarizer",
    # Multi-room — stable
    "MultiRoomAudioManager",
    "RoomAudioChunk",
    "RoomConfig",
    # Streaming — stable
    "StreamingTranscriptionConfig",
    "TranscriptionChunk",
    "TranscriptionResponse",
    "TranscriptionSegment",
    # Provisional
    "WhisperLiveConfig",
    "WhisperLiveSTTProvider",
    "WhisperLiveTranscriber",
    # Version
    "__version__",
    "get_default_provider",
    # Factory — stable
    "get_provider",
    "list_providers",
]
