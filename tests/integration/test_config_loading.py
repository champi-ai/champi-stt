"""Integration tests for configuration loading."""

import tempfile
from pathlib import Path

import pytest
import yaml

from champi_stt.assistant.service import AssistantConfig


@pytest.mark.integration
class TestConfigurationLoading:
    """Integration tests for configuration loading from files and environment."""

    def test_load_from_yaml_file(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "stt": {
                "provider": "whisperlive",
                "model_size": "base",
                "device": "cpu",
            },
            "wakeword": {
                "engine": "openwakeword",
                "keywords": ["hey_jarvis", "alexa"],
                "sensitivity": 0.7,
            },
            "commands": {
                "file": None,
                "enable_builtin": True,
            },
            "service": {
                "continuous_mode": True,
                "max_recording_duration": 15.0,
                "log_level": "DEBUG",
            },
            "ipc": {
                "memory_prefix": "test_assistant",
                "ui_window_x": 100,
                "ui_window_y": 200,
                "ui_poll_rate_hz": 30,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = AssistantConfig.from_file(config_path)

            # Verify STT config
            assert config.stt_provider == "whisperlive"
            assert config.stt_config["model_size"] == "base"
            assert config.stt_config["device"] == "cpu"

            # Verify wakeword config
            assert config.wakeword_engine == "openwakeword"
            assert config.wakeword_keywords == ["hey_jarvis", "alexa"]
            assert config.wakeword_sensitivity == 0.7

            # Verify service config
            assert config.continuous_mode is True
            assert config.max_recording_duration == 15.0
            assert config.log_level == "DEBUG"

            # Verify IPC config
            assert config.ipc_memory_prefix == "test_assistant"
            assert config.ipc_ui_window_x == 100
            assert config.ipc_ui_window_y == 200
            assert config.ipc_ui_poll_rate_hz == 30

        finally:
            Path(config_path).unlink()

    def test_load_with_defaults(self):
        """Test loading config with missing fields uses defaults."""
        config_data = {
            "stt": {"provider": "whisperlive"},
            "wakeword": {"keywords": ["test"]},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = AssistantConfig.from_file(config_path)

            # Should have defaults
            assert config.wakeword_engine == "openwakeword"  # Default
            assert config.wakeword_sensitivity == 0.5  # Default
            assert config.continuous_mode is True  # Default
            assert config.ipc_memory_prefix == "champi_assistant"  # Default

        finally:
            Path(config_path).unlink()

    def test_save_and_reload_config(self):
        """Test saving config and reloading produces same values."""
        original_config = AssistantConfig(
            stt_provider="whisperlive",
            wakeword_engine="openwakeword",
            wakeword_keywords=["test_word"],
            wakeword_sensitivity=0.8,
            continuous_mode=False,
            max_recording_duration=20.0,
            ipc_memory_prefix="custom_prefix",
            ipc_ui_window_x=150,
            ipc_ui_window_y=250,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_path = f.name

        try:
            # Save
            original_config.save(config_path)

            # Reload
            loaded_config = AssistantConfig.from_file(config_path)

            # Verify all fields match
            assert loaded_config.stt_provider == original_config.stt_provider
            assert loaded_config.wakeword_engine == original_config.wakeword_engine
            assert loaded_config.wakeword_keywords == original_config.wakeword_keywords
            assert (
                loaded_config.wakeword_sensitivity
                == original_config.wakeword_sensitivity
            )
            assert loaded_config.continuous_mode == original_config.continuous_mode
            assert (
                loaded_config.max_recording_duration
                == original_config.max_recording_duration
            )
            assert loaded_config.ipc_memory_prefix == original_config.ipc_memory_prefix
            assert loaded_config.ipc_ui_window_x == original_config.ipc_ui_window_x
            assert loaded_config.ipc_ui_window_y == original_config.ipc_ui_window_y

        finally:
            Path(config_path).unlink()

    def test_invalid_config_file(self):
        """Test handling of invalid config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content:")
            config_path = f.name

        try:
            with pytest.raises(yaml.YAMLError):
                AssistantConfig.from_file(config_path)
        finally:
            Path(config_path).unlink()

    def test_nonexistent_config_file(self):
        """Test handling of nonexistent config file."""
        with pytest.raises(FileNotFoundError):
            AssistantConfig.from_file("/nonexistent/path/config.yaml")

    def test_ipc_config_properly_loaded(self):
        """Test that IPC config is loaded from ipc: section, not service:."""
        config_data = {
            "stt": {"provider": "whisperlive"},
            "wakeword": {"keywords": ["test"]},
            "service": {
                "continuous_mode": True,
                # These should NOT be used for IPC
                "memory_prefix": "wrong_prefix",
            },
            "ipc": {
                # These should be used
                "memory_prefix": "correct_prefix",
                "ui_window_x": 999,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = AssistantConfig.from_file(config_path)

            # Verify IPC config came from ipc: section
            assert config.ipc_memory_prefix == "correct_prefix"
            assert config.ipc_ui_window_x == 999

        finally:
            Path(config_path).unlink()
