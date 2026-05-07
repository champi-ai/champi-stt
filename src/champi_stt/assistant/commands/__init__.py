"""
Command System
==============

Voice command registration and execution system.

Features:
- Exact phrase matching
- Regex pattern matching
- Multiple action types (shell, API, Python function)
- YAML configuration loading
"""

from champi_stt.assistant.commands.executor import CommandAction, CommandExecutor
from champi_stt.assistant.commands.parser import CommandParser
from champi_stt.assistant.commands.registry import CommandRegistry

__all__ = [
    "CommandAction",
    "CommandExecutor",
    "CommandParser",
    "CommandRegistry",
]
