"""
Base configuration class for all STT providers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class BaseSTTConfig(ABC):
    """
    Base configuration for all STT providers.

    Provider-specific configs should inherit from this class and add their own fields.
    """

    # Common parameters for all providers
    language: str | None = None  # Language code (None = auto-detect)
    task: str = "transcribe"  # "transcribe" or "translate"

    # Audio configuration
    audio_format: str = "wav"
    sample_rate: int = 16000
    input_device: str | None = None

    # Voice Activity Detection (generic WebRTC VAD, not provider-specific)
    disable_silence_detection: bool = False
    silence_threshold_ms: int = 800
    min_recording_duration: float = 0.3
    vad_aggressiveness: float = 2.0
    vad_chunk_duration_ms: int = 30
    initial_silence_grace_period: float = 3.0

    # Caching and storage
    cache_dir: str = "~/.cache/champi-stt"
    save_transcriptions: bool = False
    transcriptions_dir: str = "~/.cache/champi-stt/transcriptions"

    # Event system
    enable_events: bool = True
    event_emit_interval: float = 1.0

    # Logging
    log_level: str = "INFO"
    log_file: str | None = None

    @classmethod
    @abstractmethod
    def from_env(cls) -> "BaseSTTConfig":
        """
        Create configuration from environment variables.

        Each provider should implement this to load provider-specific env vars.
        """
        pass

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "BaseSTTConfig":
        """
        Create config from dictionary.

        Default implementation filters to valid dataclass fields.
        Providers can override for custom logic.
        """
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_dict = {k: v for k, v in config_dict.items() if k in valid_keys}
        return cls(**filtered_dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary"""
        result = {}
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            result[field_name] = value
        return result

    def validate_directories(self) -> None:
        """
        Validate and create cache/transcription directories.

        Default implementation - providers can override.
        """
        import os
        from pathlib import Path

        # Expand and create cache directory
        cache_path = Path(os.path.expanduser(self.cache_dir))
        cache_path.mkdir(parents=True, exist_ok=True)
        self.cache_dir = str(cache_path)

        # Expand and create transcriptions directory if enabled
        if self.save_transcriptions:
            trans_path = Path(os.path.expanduser(self.transcriptions_dir))
            trans_path.mkdir(parents=True, exist_ok=True)
            self.transcriptions_dir = str(trans_path)


# Alias for backwards compatibility with tests
BaseProviderConfig = BaseSTTConfig
