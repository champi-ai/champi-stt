"""
Assistant service configuration
"""

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import yaml
import os


@dataclass
class AssistantConfig:
    """Configuration for voice assistant service"""

    # STT Provider configuration
    stt_provider: str = "whisperlive"  # Provider type
    stt_config: dict = field(default_factory=dict)  # Provider-specific config

    # Wake word configuration
    wakeword_engine: str = "porcupine"  # Wake word engine type
    wakeword_keywords: list[str] = field(default_factory=lambda: ["jarvis"])
    wakeword_sensitivity: float = 0.5
    wakeword_access_key: Optional[str] = None  # For Porcupine

    # Command configuration
    commands_file: Optional[str] = None  # Path to commands config file
    enable_builtin_commands: bool = True

    # Service behavior
    continuous_mode: bool = True  # Keep listening after commands
    auto_start: bool = False  # Start on system boot
    max_recording_duration: float = 10.0  # Max command recording duration

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # Directories
    config_dir: str = "~/.config/champi-stt"
    cache_dir: str = "~/.cache/champi-stt"

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
        commands_config = config_dict.get("commands", {})
        service_config = config_dict.get("service", {})

        return cls(
            # STT
            stt_provider=stt_config.get("provider", "whisperlive"),
            stt_config={k: v for k, v in stt_config.items() if k != "provider"},

            # Wake word
            wakeword_engine=wakeword_config.get("engine", "porcupine"),
            wakeword_keywords=wakeword_config.get("keywords", ["jarvis"]),
            wakeword_sensitivity=wakeword_config.get("sensitivity", 0.5),
            wakeword_access_key=wakeword_config.get("access_key"),

            # Commands
            commands_file=commands_config.get("file"),
            enable_builtin_commands=commands_config.get("enable_builtin", True),

            # Service
            continuous_mode=service_config.get("continuous_mode", True),
            auto_start=service_config.get("auto_start", False),
            max_recording_duration=service_config.get("max_recording_duration", 10.0),
            log_level=service_config.get("log_level", "INFO"),
            log_file=service_config.get("log_file"),
            config_dir=service_config.get("config_dir", "~/.config/champi-stt"),
            cache_dir=service_config.get("cache_dir", "~/.cache/champi-stt"),
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

        config_dict = {
            "stt": {
                "provider": self.stt_provider,
                **self.stt_config,
            },
            "wakeword": {
                "engine": self.wakeword_engine,
                "keywords": self.wakeword_keywords,
                "sensitivity": self.wakeword_sensitivity,
                "access_key": self.wakeword_access_key,
            },
            "commands": {
                "file": self.commands_file,
                "enable_builtin": self.enable_builtin_commands,
            },
            "service": {
                "continuous_mode": self.continuous_mode,
                "auto_start": self.auto_start,
                "max_recording_duration": self.max_recording_duration,
                "log_level": self.log_level,
                "log_file": self.log_file,
                "config_dir": self.config_dir,
                "cache_dir": self.cache_dir,
            },
        }

        with open(config_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
