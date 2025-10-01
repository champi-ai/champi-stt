"""
WhisperLive STT Configuration
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from champi_stt.providers.whisperlive.enums import DeviceType, ComputeType, ModelSize, AudioFormat


@dataclass
class WhisperLiveConfig:
    """Configuration for WhisperLive STT provider."""

    # Model configuration
    model_size: str = "large-v3"  # Model size or path
    language: str | None = "en"  # Auto-detect if None
    task: str = "transcribe"  # transcribe or translate

    device: str | None = "cuda"  # Default to CPU for stability
    compute_type: str | None = "int8"  # Optimal for CPU
    cpu_threads: int = 0  # 0 = auto

    # Audio processing
    vad_filter: bool = True  # Enable VAD
    vad_parameters: dict[str, Any] | None = None
    word_timestamps: bool = False

    # Audio format configuration
    audio_format: str = "wav"  # Input audio format for STT
    sample_rate: int = 16000  # Sample rate for audio processing
    input_device: str | None = None  # Audio input device name

    # Silence detection configuration
    disable_silence_detection: bool = False  # Global disable for silence detection
    silence_threshold_ms: int = 800  # Silence threshold in milliseconds
    min_recording_duration: float = 0.3  # Minimum recording duration
    vad_aggressiveness: float = 2.0  # VAD aggressiveness (0-3)
    vad_chunk_duration_ms: int = 30  # VAD chunk duration in milliseconds
    initial_silence_grace_period: float = 3.0  # Initial silence grace period in seconds

    # Performance
    beam_size: int = 5
    best_of: int = 5
    temperature: float = 0.0
    compression_ratio_threshold: float = 2.4
    log_prob_threshold: float = -1.0
    no_speech_threshold: float = 0.6

    # Batching
    batch_size: int = 8
    chunk_length: int | None = None

    # Cache
    cache_dir: str = "/mnt/raid_0_drive/mcp_projs/champi/mcp_champi/whisper_cache"
    
    # Event system configuration
    enable_events: bool = True
    event_emit_interval: float = 1.0  # Interval for periodic event emission
    
    # Transcription saving
    save_transcriptions: bool = False
    transcriptions_dir: str = "~/.cache/mcp-champi/transcriptions"

    def __post_init__(self):
        """Post-initialization validation"""
        # Validate model size
        if self.model_size not in ModelSize.get_all_sizes():
            logger.warning(f"Unknown model size: {self.model_size}, using 'large-v3'")
            self.model_size = "large-v3"
        
        # Validate language for English-only models
        if self.is_english_only_model() and self.language and self.language != "en":
            logger.warning(f"Model {self.model_size} only supports English, setting language to 'en'")
            self.language = "en"
        
        # Validate task
        valid_tasks = ["transcribe", "translate"]
        if self.task not in valid_tasks:
            logger.warning(f"Invalid task: {self.task}, using 'transcribe'")
            self.task = "transcribe"
        
        # Validate temperature
        if not (0.0 <= self.temperature <= 1.0):
            logger.warning(f"Temperature must be between 0.0 and 1.0: {self.temperature}, using 0.0")
            self.temperature = 0.0
        
        # Validate beam size
        if self.beam_size < 1:
            logger.warning(f"Beam size must be >= 1: {self.beam_size}, using 5")
            self.beam_size = 5
        
        # Validate batch size
        if self.batch_size < 1:
            logger.warning(f"Batch size must be >= 1: {self.batch_size}, using 8")
            self.batch_size = 8
        
        # Validate VAD aggressiveness
        if not (0.0 <= self.vad_aggressiveness <= 3.0):
            logger.warning(f"VAD aggressiveness must be between 0.0 and 3.0: {self.vad_aggressiveness}, using 2.0")
            self.vad_aggressiveness = 2.0
        
        # Validate silence threshold
        if self.silence_threshold_ms < 100:
            logger.warning(f"Silence threshold too low: {self.silence_threshold_ms}ms, using 800ms")
            self.silence_threshold_ms = 800
        
        # Validate minimum recording duration
        if self.min_recording_duration < 0.1:
            logger.warning(f"Minimum recording duration too low: {self.min_recording_duration}s, using 0.3s")
            self.min_recording_duration = 0.3

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "WhisperLiveConfig":
        """Create config from dictionary"""
        # Filter out unknown keys
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_dict = {k: v for k, v in config_dict.items() if k in valid_keys}

        return cls(**filtered_dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary"""
        result = {}
        for field_name, _field_def in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            result[field_name] = value
        return result

    @classmethod
    def from_file(cls, config_path: str) -> "WhisperLiveConfig":
        """Load config from JSON file"""
        try:
            with open(config_path) as f:
                config_dict = json.load(f)
            return cls.from_dict(config_dict)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return cls()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {config_path} - {e}")
            return cls()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return cls()

    @classmethod
    def from_env(cls) -> "WhisperLiveConfig":
        """Create configuration from environment variables"""
        config = cls()
        
        # Model settings
        if env_value := os.environ.get("WHISPERLIVE_MODEL"):
            config.model_size = env_value
        if env_value := os.environ.get("WHISPERLIVE_LANGUAGE"):
            config.language = env_value
        if env_value := os.environ.get("WHISPERLIVE_TASK"):
            config.task = env_value

        # Device settings
        if env_value := os.environ.get("WHISPERLIVE_DEVICE"):
            config.device = env_value
        if env_value := os.environ.get("WHISPERLIVE_COMPUTE_TYPE"):
            config.compute_type = env_value
        if env_value := os.environ.get("WHISPERLIVE_CPU_THREADS"):
            try:
                config.cpu_threads = int(env_value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid WHISPERLIVE_CPU_THREADS={env_value}: {e}")

        # Audio processing
        if env_value := os.environ.get("WHISPERLIVE_DISABLE_VAD"):
            config.vad_filter = not (env_value.lower() in ["true", "1", "yes", "on"])
        if env_value := os.environ.get("WHISPERLIVE_WORD_TIMESTAMPS"):
            config.word_timestamps = env_value.lower() in ["true", "1", "yes", "on"]

        # Audio format settings
        if env_value := os.environ.get("CHAMPI_STT_AUDIO_FORMAT"):
            config.audio_format = env_value
        if env_value := os.environ.get("CHAMPI_SAMPLE_RATE"):
            try:
                config.sample_rate = int(env_value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid CHAMPI_SAMPLE_RATE={env_value}: {e}")
        if env_value := os.environ.get("CHAMPI_INPUT_DEVICE"):
            config.input_device = env_value

        # Silence detection settings
        if env_value := os.environ.get("CHAMPI_DISABLE_SILENCE_DETECTION"):
            config.disable_silence_detection = env_value.lower() in ["true", "1", "yes", "on"]
        if env_value := os.environ.get("CHAMPI_SILENCE_THRESHOLD_MS"):
            try:
                config.silence_threshold_ms = int(env_value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid CHAMPI_SILENCE_THRESHOLD_MS={env_value}: {e}")
        if env_value := os.environ.get("CHAMPI_MIN_RECORDING_DURATION"):
            try:
                config.min_recording_duration = float(env_value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid CHAMPI_MIN_RECORDING_DURATION={env_value}: {e}")
        if env_value := os.environ.get("CHAMPI_VAD_AGGRESSIVENESS"):
            try:
                config.vad_aggressiveness = float(env_value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid CHAMPI_VAD_AGGRESSIVENESS={env_value}: {e}")
        if env_value := os.environ.get("CHAMPI_VAD_CHUNK_DURATION_MS"):
            try:
                config.vad_chunk_duration_ms = int(env_value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid CHAMPI_VAD_CHUNK_DURATION_MS={env_value}: {e}")
        if env_value := os.environ.get("CHAMPI_INITIAL_SILENCE_GRACE_PERIOD"):
            try:
                config.initial_silence_grace_period = float(env_value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid CHAMPI_INITIAL_SILENCE_GRACE_PERIOD={env_value}: {e}")

        # Performance
        if env_value := os.environ.get("WHISPERLIVE_BEAM_SIZE"):
            try:
                config.beam_size = int(env_value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid WHISPERLIVE_BEAM_SIZE={env_value}: {e}")
        if env_value := os.environ.get("WHISPERLIVE_BEST_OF"):
            try:
                config.best_of = int(env_value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid WHISPERLIVE_BEST_OF={env_value}: {e}")
        if env_value := os.environ.get("WHISPERLIVE_TEMPERATURE"):
            try:
                config.temperature = float(env_value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid WHISPERLIVE_TEMPERATURE={env_value}: {e}")
        if env_value := os.environ.get("WHISPERLIVE_BATCH_SIZE"):
            try:
                config.batch_size = int(env_value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid WHISPERLIVE_BATCH_SIZE={env_value}: {e}")

        # Cache
        if env_value := os.environ.get("WHISPERLIVE_CACHE_DIR"):
            config.cache_dir = env_value

        # Event system
        if env_value := os.environ.get("WHISPERLIVE_ENABLE_EVENTS"):
            config.enable_events = env_value.lower() in ["true", "1", "yes", "on"]
        if env_value := os.environ.get("WHISPERLIVE_EVENT_INTERVAL"):
            try:
                config.event_emit_interval = float(env_value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid WHISPERLIVE_EVENT_INTERVAL={env_value}: {e}")

        # Transcription saving
        if env_value := os.environ.get("WHISPERLIVE_SAVE_TRANSCRIPTIONS"):
            config.save_transcriptions = env_value.lower() in ["true", "1", "yes", "on"]
        if env_value := os.environ.get("WHISPERLIVE_TRANSCRIPTIONS_DIR"):
            config.transcriptions_dir = env_value

        return config

    @property
    def model_sizes(self) -> list[str]:
        """Available model sizes."""
        return ModelSize.get_all_sizes()

    def is_english_only_model(self) -> bool:
        """Check if the model is English-only."""
        return ModelSize.is_english_only(self.model_size)

    def get_effective_language(self) -> str | None:
        """Get the effective language considering model constraints."""
        if self.is_english_only_model():
            return "en"
        return self.language

    def get_device(self) -> str:
        """Determine the device to use"""
        if self.device == "cpu":
            return "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            logger.warning("PyTorch not available, falling back to CPU")
        return "cpu"

    @property
    def supported_audio_formats(self) -> list[str]:
        """Get list of audio formats supported by WhisperLive STT."""
        return [format.value for format in AudioFormat]

    def validate_audio_format(self) -> str:
        """Validate and return a supported audio format."""
        if self.audio_format in self.supported_audio_formats:
            return self.audio_format

        # Fallback to wav if format is not supported
        logger.warning(
            f"Audio format '{self.audio_format}' not supported by WhisperLive, using 'wav'"
        )
        return "wav"

    def validate_directories(self) -> None:
        """Validate and create cache directory if needed."""
        from pathlib import Path

        try:
            # Expand the cache directory path
            expanded_cache_dir = self.cache_dir
            cache_path = Path(expanded_cache_dir)

            # Create the cache directory
            cache_path.mkdir(parents=True, exist_ok=True)

            # Update the cache_dir to the expanded path for consistency
            self.cache_dir = str(cache_path)

            logger.debug(f"WhisperLive cache directory validated: {self.cache_dir}")

        except Exception as e:
            logger.error(
                f"Failed to create WhisperLive cache directory '{self.cache_dir}': {e}"
            )
            # Set fallback cache directory
            fallback_cache = os.path.expanduser("~/.cache/whisper-live/")
            try:
                Path(fallback_cache).mkdir(parents=True, exist_ok=True)
                self.cache_dir = fallback_cache
                logger.warning(f"Using fallback cache directory: {fallback_cache}")
            except Exception as fallback_error:
                logger.error(
                    f"Failed to create fallback cache directory: {fallback_error}"
                )
                raise


class WhisperPresets:
    """Predefined configuration presets for WhisperLive STT"""

    @staticmethod
    def performance() -> WhisperLiveConfig:
        """High-performance configuration optimized for speed"""
        return WhisperLiveConfig(
            model_size="large-v3-turbo",
            device="cuda",
            compute_type="float16",
            vad_filter=True,
            beam_size=1,  # Faster beam search
            best_of=1,
            temperature=0.0,
            batch_size=16,  # Larger batch for better throughput
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
            word_timestamps=False,  # Disable for speed
            silence_threshold_ms=500,  # More responsive
            min_recording_duration=0.2,
            vad_aggressiveness=2.0,
        )

    @staticmethod
    def quality() -> WhisperLiveConfig:
        """High-quality configuration optimized for accuracy"""
        return WhisperLiveConfig(
            model_size="large-v3",
            device="cuda",
            compute_type="float16",
            vad_filter=True,
            beam_size=5,  # Better beam search
            best_of=5,
            temperature=0.0,
            batch_size=8,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
            word_timestamps=True,  # Enable for detailed output
            silence_threshold_ms=800,
            min_recording_duration=0.3,
            vad_aggressiveness=2.0,
        )

    @staticmethod
    def cpu_only() -> WhisperLiveConfig:
        """CPU-only configuration for systems without CUDA"""
        return WhisperLiveConfig(
            model_size="medium",  # Smaller model for CPU
            device="cpu",
            compute_type="int8",
            cpu_threads=0,  # Auto-detect
            vad_filter=True,
            beam_size=3,  # Reduced for CPU
            best_of=3,
            temperature=0.0,
            batch_size=4,  # Smaller batch for CPU
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
            word_timestamps=False,
            silence_threshold_ms=800,
            min_recording_duration=0.3,
            vad_aggressiveness=1.0,  # Less aggressive for CPU
        )

    @staticmethod
    def minimal() -> WhisperLiveConfig:
        """Minimal resource configuration for low-end systems"""
        return WhisperLiveConfig(
            model_size="base",  # Smallest practical model
            device="cpu",
            compute_type="int8",
            cpu_threads=2,  # Limited threads
            vad_filter=False,  # Disable VAD to save resources
            beam_size=1,  # Minimal beam search
            best_of=1,
            temperature=0.0,
            batch_size=1,  # Single sample processing
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
            word_timestamps=False,
            silence_threshold_ms=1000,  # Less sensitive
            min_recording_duration=0.5,
            vad_aggressiveness=0.5,  # Minimal aggressiveness
        )
