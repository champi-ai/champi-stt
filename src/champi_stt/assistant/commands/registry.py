"""
Command registry for voice commands
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

# import logging - replaced with loguru
from typing import Any

from loguru import logger


@dataclass
class Command:
    """Represents a registered voice command"""

    phrase: str  # Exact phrase or regex pattern
    handler: Callable  # Function to execute
    is_pattern: bool = False  # True if phrase is regex
    description: str = ""  # Human-readable description


class CommandRegistry:
    r"""
    Registry for voice commands with exact and pattern matching.

    Examples:
        registry = CommandRegistry()

        # Exact match
        registry.register_exact("turn on lights", turn_on_lights)

        # Pattern match
        registry.register_pattern(r"set volume to (?P<level>\d+)", set_volume)

        # Execute
        await registry.execute("set volume to 50")  # Calls set_volume(level="50")
    """

    def __init__(self):
        self._exact_commands: dict[str, Command] = {}
        self._pattern_commands: list[tuple[re.Pattern, Command]] = []

    def register_exact(
        self, phrase: str, handler: Callable, description: str = ""
    ) -> None:
        """
        Register exact phrase match command.

        Args:
            phrase: Exact phrase to match (case-insensitive)
            handler: Async or sync function to execute
            description: Human-readable description
        """
        normalized_phrase = phrase.lower().strip()

        if normalized_phrase in self._exact_commands:
            logger.warning(f"Overwriting existing command: '{phrase}'")

        command = Command(
            phrase=normalized_phrase,
            handler=handler,
            is_pattern=False,
            description=description or f"Execute: {phrase}",
        )

        self._exact_commands[normalized_phrase] = command
        logger.debug(f"Registered exact command: '{phrase}'")

    def register_pattern(
        self, pattern: str, handler: Callable, description: str = ""
    ) -> None:
        r"""
        Register regex pattern command.

        Args:
            pattern: Regex pattern with optional named groups
            handler: Function to execute (receives named groups as kwargs)
            description: Human-readable description

        Example:
            registry.register_pattern(
                r"set (?P<device>\w+) to (?P<value>\d+)",
                set_device_value
            )
            # "set volume to 50" -> set_device_value(device="volume", value="50")
        """
        compiled_pattern = re.compile(pattern, re.IGNORECASE)

        command = Command(
            phrase=pattern,
            handler=handler,
            is_pattern=True,
            description=description or f"Pattern: {pattern}",
        )

        self._pattern_commands.append((compiled_pattern, command))
        logger.debug(f"Registered pattern command: '{pattern}'")

    def unregister(self, phrase: str) -> bool:
        """
        Unregister a command.

        Args:
            phrase: Exact phrase or pattern to remove

        Returns:
            True if command was found and removed
        """
        normalized = phrase.lower().strip()

        # Try exact match first
        if normalized in self._exact_commands:
            del self._exact_commands[normalized]
            logger.debug(f"Unregistered exact command: '{phrase}'")
            return True

        # Try pattern match
        for i, (_pattern, command) in enumerate(self._pattern_commands):
            if command.phrase == phrase:
                self._pattern_commands.pop(i)
                logger.debug(f"Unregistered pattern command: '{phrase}'")
                return True

        return False

    async def execute(
        self, transcription: str, context: dict[str, Any] | None = None
    ) -> Any | None:
        """
        Execute command based on transcription.

        Tries exact match first, then pattern matching.

        Args:
            transcription: Transcribed user speech
            context: Optional context dict (e.g., speaker info, timestamp, etc.)

        Returns:
            Result from command handler, or None if no match
        """
        text = transcription.lower().strip()
        context = context or {}

        logger.debug(f"Matching command for: '{text}'")

        # Try exact match first (faster)
        if text in self._exact_commands:
            command = self._exact_commands[text]
            logger.info(f"✓ Matched exact command: '{command.phrase}'")
            return await self._execute_handler(command.handler, context)

        # Try pattern matching
        for pattern, command in self._pattern_commands:
            match = pattern.match(text)
            if match:
                logger.info(f"✓ Matched pattern command: '{command.phrase}'")
                kwargs = {**match.groupdict(), **context}
                return await self._execute_handler(command.handler, kwargs)

        logger.debug(f"No command matched for: '{text}'")
        return None

    async def _execute_handler(self, handler: Callable, kwargs: dict[str, Any]) -> Any:
        """
        Execute command handler (async or sync).

        Args:
            handler: Function to execute
            kwargs: Keyword arguments from regex groups

        Returns:
            Handler result
        """
        import asyncio

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**kwargs)
            else:
                result = handler(**kwargs)

            logger.debug(f"Command executed successfully: {result}")
            return result

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise

    def list_commands(self) -> list[dict[str, Any]]:
        """
        List all registered commands.

        Returns:
            List of command info dicts
        """
        commands = []

        # Add exact commands
        for phrase, command in self._exact_commands.items():
            commands.append(
                {
                    "type": "exact",
                    "phrase": phrase,
                    "description": command.description,
                }
            )

        # Add pattern commands
        for _pattern, command in self._pattern_commands:
            commands.append(
                {
                    "type": "pattern",
                    "phrase": command.phrase,
                    "description": command.description,
                }
            )

        return commands

    def clear(self) -> None:
        """Clear all registered commands"""
        self._exact_commands.clear()
        self._pattern_commands.clear()
        logger.debug("All commands cleared")

    def __len__(self) -> int:
        """Get total number of registered commands"""
        return len(self._exact_commands) + len(self._pattern_commands)
