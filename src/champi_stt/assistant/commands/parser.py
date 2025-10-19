"""
Command parser for intent extraction
"""

# import logging - replaced with loguru
from dataclasses import dataclass
from typing import Optional, Any
import yaml
import json
from pathlib import Path

from champi_stt.assistant.commands.registry import CommandRegistry
from champi_stt.assistant.commands.executor import CommandExecutor, CommandAction, ActionType

from loguru import logger


@dataclass
class CommandMatch:
    """Represents a matched command with its parameters."""

    command_name: str  # Name/identifier of the matched command
    matched_text: str  # The text that was matched
    confidence: float  # Match confidence score (0.0-1.0)
    parameters: dict[str, Any]  # Extracted parameters from the match


class CommandParser:
    """
    Parse and load commands from configuration files.

    Supports YAML and JSON configuration files.
    """

    def __init__(self, registry: CommandRegistry, executor: CommandExecutor):
        self.registry = registry
        self.executor = executor

    async def load_from_file(self, config_path: str | Path) -> int:
        """
        Load commands from YAML or JSON file.

        Args:
            config_path: Path to configuration file

        Returns:
            Number of commands loaded

        Example config (YAML):
            exact:
              "turn on lights":
                type: "api"
                url: "http://192.168.1.100/api/lights/on"
                method: "POST"

              "what time is it":
                type: "python"
                function: "builtins.say_time"

            patterns:
              "set volume to (?P<level>\\d+)":
                type: "shell"
                command: "pactl set-sink-volume @DEFAULT_SINK@ {level}%"
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        logger.info(f"Loading commands from: {config_path}")

        # Load config file
        with open(config_path) as f:
            if config_path.suffix in [".yaml", ".yml"]:
                config = yaml.safe_load(f)
            elif config_path.suffix == ".json":
                config = json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {config_path.suffix}")

        commands_loaded = 0

        # Load exact commands
        if "exact" in config:
            for phrase, action_config in config["exact"].items():
                handler = self._create_handler(action_config)
                description = action_config.get("description", "")
                self.registry.register_exact(phrase, handler, description)
                commands_loaded += 1

        # Load pattern commands
        if "patterns" in config:
            for pattern, action_config in config["patterns"].items():
                handler = self._create_handler(action_config)
                description = action_config.get("description", "")
                self.registry.register_pattern(pattern, handler, description)
                commands_loaded += 1

        logger.info(f"✓ Loaded {commands_loaded} commands from {config_path}")
        return commands_loaded

    def _create_handler(self, action_config: dict[str, Any]):
        """
        Create command handler from action configuration.

        Args:
            action_config: Action configuration dict

        Returns:
            Async handler function
        """
        action_type = ActionType(action_config["type"])

        if action_type == ActionType.SHELL:
            command = action_config["command"]
            timeout = action_config.get("timeout", 30)

            async def shell_handler(**kwargs):
                return await self.executor.execute_shell(command, timeout=timeout, **kwargs)

            return shell_handler

        elif action_type == ActionType.API:
            url = action_config["url"]
            method = action_config.get("method", "GET")
            headers = action_config.get("headers")
            data = action_config.get("data")
            timeout = action_config.get("timeout", 30)

            async def api_handler(**kwargs):
                return await self.executor.execute_api(
                    url, method=method, headers=headers, data=data, timeout=timeout, **kwargs
                )

            return api_handler

        elif action_type == ActionType.PYTHON:
            function_path = action_config["function"]
            args = action_config.get("args", [])

            async def python_handler(**kwargs):
                # Merge configured args with runtime kwargs
                all_kwargs = {**dict(enumerate(args)), **kwargs}
                return await self.executor.execute_python(function_path, **all_kwargs)

            return python_handler

        else:
            raise ValueError(f"Unknown action type: {action_type}")

    async def load_from_dict(self, config: dict[str, Any]) -> int:
        """
        Load commands from dictionary.

        Args:
            config: Configuration dictionary

        Returns:
            Number of commands loaded
        """
        commands_loaded = 0

        # Load exact commands
        if "exact" in config:
            for phrase, action_config in config["exact"].items():
                handler = self._create_handler(action_config)
                description = action_config.get("description", "")
                self.registry.register_exact(phrase, handler, description)
                commands_loaded += 1

        # Load pattern commands
        if "patterns" in config:
            for pattern, action_config in config["patterns"].items():
                handler = self._create_handler(action_config)
                description = action_config.get("description", "")
                self.registry.register_pattern(pattern, handler, description)
                commands_loaded += 1

        logger.info(f"✓ Loaded {commands_loaded} commands from dict")
        return commands_loaded
