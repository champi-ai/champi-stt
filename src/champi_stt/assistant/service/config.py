"""
Assistant service configuration
"""

import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class AssistantConfig:
    """Configuration for voice assistant service"""

    # STT Provider configuration
    stt_provider: str = "whisperlive"  # Provider type
    stt_config: dict = field(default_factory=dict)  # Provider-specific config

    # Wake word configuration
    wakeword_engine: str = "openwakeword"  # Wake word engine type
    wakeword_keywords: list[str] = field(default_factory=lambda: ["hey_jarvis"])
    wakeword_sensitivity: float = 0.5
    wakeword_access_key: str | None = None  # Deprecated (was for Porcupine)

    # Audio configuration
    input_device: str | None = None  # Audio input device name (None = default)

    # Command configuration
    commands_file: str | None = None  # Path to commands config file
    enable_builtin_commands: bool = True

    # Service behavior
    continuous_mode: bool = True  # Keep listening after commands
    auto_start: bool = False  # Start on system boot
    max_recording_duration: float = 10.0  # Max command recording duration
    command_silence_timeout_ms: int = 2500  # Silence timeout for command recording (ms)
    enable_visualizer: bool = False  # Show real-time spectrogram
    enable_wake_indicator: bool = False  # Show visual wake status indicator
    wake_indicator_position: str | None = (
        None  # DEPRECATED: Position no longer configurable
    )
    enable_speaker_identification: bool = (
        False  # Enable speaker identification from wake word
    )
    speaker_identification_threshold: float = (
        0.75  # Similarity threshold for speaker ID
    )

    # IPC Configuration
    ipc_memory_prefix: str = "champi_assistant"  # Shared memory namespace prefix
    ipc_ui_window_x: int = 50  # UI window X position
    ipc_ui_window_y: int = 50  # UI window Y position
    ipc_ui_poll_rate_hz: int = 60  # UI signal polling rate

    # Logging
    log_level: str = "INFO"
    log_file: str | None = None

    # Directories
    config_dir: str = "~/.config/champi-stt"
    cache_dir: str = "~/.cache/champi-stt"

    def __post_init__(self):
        """Post-initialization to handle deprecation warnings"""
        if self.wake_indicator_position is not None:
            warnings.warn(
                "wake_indicator_position is deprecated and no longer used. "
                "UI window position is now configured via ipc_ui_window_x and ipc_ui_window_y.",
                DeprecationWarning,
                stacklevel=2,
            )

    @classmethod
    def from_file(cls, config_path: str | Path) -> "AssistantConfig":
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file

        Returns:
            AssistantConfig instance
        """
        config_path = Path(config_path).expanduser()

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            config_dict = yaml.safe_load(f)

        return cls.from_dict(config_dict)

    @classmethod
    def from_dict(cls, config_dict: dict) -> "AssistantConfig":
        """Create config from dictionary"""
        # Extract top-level keys
        stt_config = config_dict.get("stt", {})
        wakeword_config = config_dict.get("wakeword", {})
        audio_config = config_dict.get("audio", {})
        commands_config = config_dict.get("commands", {})
        service_config = config_dict.get("service", {})
        ipc_config = config_dict.get("ipc", {})

        return cls(
            # STT
            stt_provider=stt_config.get("provider", "whisperlive"),
            stt_config={k: v for k, v in stt_config.items() if k != "provider"},
            # Wake word
            wakeword_engine=wakeword_config.get("engine", "openwakeword"),
            wakeword_keywords=wakeword_config.get("keywords", ["hey_jarvis"]),
            wakeword_sensitivity=wakeword_config.get("sensitivity", 0.5),
            wakeword_access_key=wakeword_config.get("access_key"),
            # Audio
            input_device=audio_config.get("input_device"),
            # Commands
            commands_file=commands_config.get("file"),
            enable_builtin_commands=commands_config.get("enable_builtin", True),
            # Service
            continuous_mode=service_config.get("continuous_mode", True),
            auto_start=service_config.get("auto_start", False),
            max_recording_duration=service_config.get("max_recording_duration", 10.0),
            command_silence_timeout_ms=service_config.get(
                "command_silence_timeout_ms", 2500
            ),
            enable_visualizer=service_config.get("enable_visualizer", False),
            enable_wake_indicator=service_config.get("enable_wake_indicator", False),
            wake_indicator_position=service_config.get(
                "wake_indicator_position"
            ),  # Deprecated
            enable_speaker_identification=service_config.get(
                "enable_speaker_identification", False
            ),
            speaker_identification_threshold=service_config.get(
                "speaker_identification_threshold", 0.75
            ),
            log_level=service_config.get("log_level", "INFO"),
            log_file=service_config.get("log_file"),
            config_dir=service_config.get("config_dir", "~/.config/champi-stt"),
            cache_dir=service_config.get("cache_dir", "~/.config/champi-stt"),
            # IPC
            ipc_memory_prefix=ipc_config.get("memory_prefix", "champi_assistant"),
            ipc_ui_window_x=ipc_config.get("ui_window_x", 50),
            ipc_ui_window_y=ipc_config.get("ui_window_y", 50),
            ipc_ui_poll_rate_hz=ipc_config.get("ui_poll_rate_hz", 60),
        )

    @classmethod
    def from_env(cls) -> "AssistantConfig":
        """Create configuration from environment variables"""
        config = cls()

        # Check for config file path in env
        if config_file := os.getenv("CHAMPI_CONFIG_FILE"):
            return cls.from_file(config_file)

        # Otherwise load from individual env vars
        if provider := os.getenv("CHAMPI_STT_PROVIDER"):
            config.stt_provider = provider

        if keywords := os.getenv("CHAMPI_WAKEWORD_KEYWORDS"):
            config.wakeword_keywords = keywords.split(",")

        if access_key := os.getenv("CHAMPI_WAKEWORD_ACCESS_KEY"):
            config.wakeword_access_key = access_key

        if log_level := os.getenv("CHAMPI_LOG_LEVEL"):
            config.log_level = log_level

        return config

    def save(self, config_path: str | Path) -> None:
        """
        Save configuration to YAML file.

        Args:
            config_path: Path to save config
        """
        config_path = Path(config_path).expanduser()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Build STT config section with all provider-specific fields
        stt_section = {
            "provider": self.stt_provider,
        }
        # Add any additional STT config fields
        if self.stt_config:
            stt_section.update(self.stt_config)

        config_dict = {
            "stt": stt_section,
            "wakeword": {
                "engine": self.wakeword_engine,
                "keywords": self.wakeword_keywords,
                "sensitivity": self.wakeword_sensitivity,
                "access_key": self.wakeword_access_key,
            },
            "audio": {
                "input_device": self.input_device,
            },
            "commands": {
                "file": self.commands_file,
                "enable_builtin": self.enable_builtin_commands,
            },
            "service": {
                "continuous_mode": self.continuous_mode,
                "auto_start": self.auto_start,
                "max_recording_duration": self.max_recording_duration,
                "command_silence_timeout_ms": self.command_silence_timeout_ms,
                "enable_visualizer": self.enable_visualizer,
                "enable_wake_indicator": self.enable_wake_indicator,
                # Deprecated: "wake_indicator_position": self.wake_indicator_position,
                "enable_speaker_identification": self.enable_speaker_identification,
                "speaker_identification_threshold": self.speaker_identification_threshold,
                "log_level": self.log_level,
                "log_file": self.log_file,
                "config_dir": self.config_dir,
                "cache_dir": self.cache_dir,
            },
            "ipc": {
                "memory_prefix": self.ipc_memory_prefix,
                "ui_window_x": self.ipc_ui_window_x,
                "ui_window_y": self.ipc_ui_window_y,
                "ui_poll_rate_hz": self.ipc_ui_poll_rate_hz,
            },
        }

        with open(config_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
