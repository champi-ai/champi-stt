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

from champi_stt.assistant.commands.registry import CommandRegistry
from champi_stt.assistant.commands.executor import CommandExecutor, CommandAction
from champi_stt.assistant.commands.parser import CommandParser

__all__ = [
    "CommandRegistry",
    "CommandExecutor",
    "CommandAction",
    "CommandParser",
]
