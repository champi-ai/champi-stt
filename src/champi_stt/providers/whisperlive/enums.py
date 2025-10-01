"""
Enums for WhisperLive STT service.
Defines message types and status codes for consistent communication.
"""

from enum import Enum, unique


@unique
class STTEventTypes(Enum):
    """Main event type categories for STT service"""
    
    LIFECYCLE_EVENT = "lifecycle_event"
    MODEL_EVENT = "model_event"  
    PROCESSING_EVENT = "processing_event"
    TELEMETRY_EVENT = "telemetry_event"


@unique
class LifecycleEvents(Enum):
    """Lifecycle Events for WhisperLive STT service"""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING_AUDIO = "processing_audio"
    TRANSCRIBING = "transcribing"
    ERROR = "error"
    SHUTDOWN = "shutdown"
    LISTENING = "listening"
    STANDBY = "standby"
    STOPPED = "stopped"
    RECORDING = "recording"
    IDLE = "idle"


@unique
class ModelEvents(Enum):
    """Model-related events"""
    
    MODEL_LOADING = "model_loading"
    MODEL_LOADED = "model_loaded"
    MODEL_UNLOADED = "model_unloaded"
    MODEL_ERROR = "model_error"
    MODEL_CACHED = "model_cached"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    DEVICE_DETECTED = "device_detected"
    DEVICE_FALLBACK = "device_fallback"
    WARMUP_START = "warmup_start"
    WARMUP_COMPLETE = "warmup_complete"
    INITIALIZING = "initializing"
    UNLOADING = "unloading"


@unique
class ProcessingEvents(Enum):
    """Audio processing and transcription events"""
    
    AUDIO_RECEIVED = "audio_received"
    AUDIO_PREPROCESSING = "audio_preprocessing" 
    AUDIO_NORMALIZED = "audio_normalized"
    TRANSCRIPTION_START = "transcription_start"
    TRANSCRIPTION_PROGRESS = "transcription_progress"
    TRANSCRIPTION_COMPLETE = "transcription_complete"
    LANGUAGE_DETECTED = "language_detected"
    VAD_PROCESSING = "vad_processing"
    SILENCE_DETECTED = "silence_detected"
    SPEECH_DETECTED = "speech_detected"
    RECORDING_START = "recording_start"
    RECORDING_STOP = "recording_stop"
    BATCH_PROCESSING = "batch_processing"


@unique
class TelemetryEvents(Enum):
    """Metrics and telemetry events"""
    
    METRICS_UPDATE = "metrics_update"
    PERFORMANCE_STATS = "performance_stats"
    USAGE_STATS = "usage_stats"
    PROCESSING_TIME = "processing_time"
    AUDIO_STATS = "audio_stats"
    MODEL_STATS = "model_stats"


@unique
class AudioFormat(Enum):
    """Supported audio input/output formats"""
    
    WAV = "wav"
    MP3 = "mp3" 
    OPUS = "opus"
    FLAC = "flac"
    M4A = "m4a"
    OGG = "ogg"


@unique
class ModelSize(Enum):
    """WhisperLive supported model sizes"""
    
    TINY = "tiny"
    TINY_EN = "tiny.en"
    BASE = "base"
    BASE_EN = "base.en"
    SMALL = "small"
    SMALL_EN = "small.en"
    MEDIUM = "medium"
    MEDIUM_EN = "medium.en"
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"
    LARGE_V3_TURBO = "large-v3-turbo"
    TURBO = "turbo"
    DISTIL_SMALL_EN = "distil-small.en"
    DISTIL_MEDIUM_EN = "distil-medium.en"
    DISTIL_LARGE_V2 = "distil-large-v2"
    DISTIL_LARGE_V3 = "distil-large-v3"
    
    @classmethod
    def get_all_sizes(cls) -> list[str]:
        """Get all supported model sizes"""
        return [model.value for model in cls]
    
    @classmethod
    def is_english_only(cls, model_size: str) -> bool:
        """Check if model is English-only"""
        return model_size.endswith(".en")


@unique
class DeviceType(Enum):
    """Supported compute devices"""
    
    CPU = "cpu"
    CUDA = "cuda"
    AUTO = "auto"


@unique
class ComputeType(Enum):
    """Supported compute types for faster-whisper"""
    
    FLOAT16 = "float16"
    FLOAT32 = "float32"
    INT8 = "int8"
    INT8_FLOAT16 = "int8_float16"
    INT8_FLOAT32 = "int8_float32"
    INT16 = "int16"
    AUTO = "auto"


@unique
class ResponseFormat(Enum):
    """Transcription response formats"""
    
    JSON = "json"
    TEXT = "text"
    VERBOSE_JSON = "verbose_json"
    SRT = "srt"
    VTT = "vtt"
    TSV = "tsv"


@unique
class TaskType(Enum):
    """Whisper task types"""
    
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"


@unique
class WhisperStrings(Enum):
    """Functional string constants used in WhisperLive STT service"""
    
    # Cache filename patterns
    MODEL_CACHE_KEY = "whisperlive_{}.pkl"
    MODEL_METADATA_KEY = "whisperlive_{}.json"
    
    # Device names
    PULSE_DEVICE = "pulse"
    USB_MIC_DEVICE = "USB Condenser Microphone"
    
    # File extensions
    WAV_EXTENSION = ".wav"
    JSON_EXTENSION = ".json"
    
    # Default directories
    DEFAULT_CACHE_DIR = "~/.cache/whisper-live/"
    DEFAULT_TRANSCRIPTIONS_DIR = "~/.cache/mcp-champi/transcriptions"


@unique
class LoggingStrings(Enum):
    """Logging message templates for WhisperLive STT service"""

    # Initialization and loading messages
    LOADING_FROM_MEMORY_CACHE = "🚀 Loading WhisperLive from memory cache..."
    LOADING_FROM_DISK_CACHE = "📦 WhisperLive model previously cached, loading..."
    LOADED_FROM_CACHE = "✅ WhisperLive loaded from cache"
    LOADING_FROM_SCRATCH = "🔄 Loading WhisperLive from scratch..."
    PROVIDER_INITIALIZED = "WhisperLive STT provider initialized successfully"
    PROVIDER_UNLOADED = "WhisperLive STT provider unloaded"
    CACHED_MODEL_METADATA = "💾 WhisperLive model metadata saved for {}"
    
    # Model and device messages  
    DEVICE_AUTO_DETECTED = "Auto-detected device: {}, compute_type: {}"
    CUDA_FALLBACK_TO_CPU = "CUDA libraries incompatible, falling back to CPU: {}"
    MODEL_LOADED_TIME = "Model loaded in {:.2f}s"
    USING_CACHED_MODEL = "Using cached WhisperLive model: {}"
    
    # Transcription and processing
    TRANSCRIBING_AUDIO = "🎤 Transcribing audio with WhisperLive"
    TRANSCRIPTION_COMPLETED = "✓ WhisperLive transcription completed - Processing: {:.2f}s, RTF: {:.2f}"
    RECORDING_AUDIO = "🎤 Recording audio for {:.1f}s..."
    RECORDING_WITH_VAD = "🎤 Recording with silence detection (max {:.1f}s)..."
    SILENCE_DETECTED_STOP = "✓ Silence detected after {:.1f}s"
    SPEECH_DETECTED_START = "Speech detected, recording..."
    AUDIO_RECORDED = "✓ Recorded {} samples ({:.1f}s)"
    
    # Language and voice detection
    LANGUAGE_DETECTED = "Detected language: {} (probability: {:.3f})"
    LANGUAGE_DETECTION_SKIPPED = "Language detection skipped: {} (using English-only model)"
    
    # Directory and file operations
    DIRECTORIES_VALIDATED = "WhisperLive cache directory validated: {}"
    CACHE_DIR_CREATED = "Created WhisperLive cache directory: {}"
    TRANSCRIPTION_SAVED = "Transcription saved to: {}"
    
    # Error messages
    CACHE_LOAD_FAILED = "Cache load failed: {}, loading fresh..."
    FAILED_TO_CACHE_MODEL = "Failed to cache model metadata: {}"
    FAILED_TO_INITIALIZE = "Failed to initialize WhisperLive provider: {}"
    TRANSCRIPTION_FAILED = "WhisperLive transcription failed: {}"
    LANGUAGE_DETECTION_FAILED = "Language detection failed: {}"
    AUDIO_PLAYBACK_FAILED = "Audio playback failed: {}"
    RECORDING_FAILED = "Recording failed: {}"
    VAD_INITIALIZATION_FAILED = "VAD initialization failed: {}"
    
    # Warning messages
    NO_SPEECH_DETECTED = "No speech detected after {:.1f}s grace period"
    EMPTY_AUDIO_CHUNKS = "No audio chunks recorded"
    EMPTY_TRANSCRIPTION = "WhisperLive returned empty text. Raw response: {}"
    MODEL_FILE_NOT_FOUND = "Model file not found: {}"
    UNSUPPORTED_AUDIO_FORMAT = "Audio format '{}' not supported, using 'wav'"
    
    # API response messages
    PROVIDER_NOT_INITIALIZED = "WhisperLive STT provider not initialized"
    MODEL_NOT_LOADED = "WhisperLive model not loaded"
    INVALID_AUDIO_DATA = "Invalid audio data provided"
    SERVICE_NOT_RUNNING = "WhisperLive STT service is not running"