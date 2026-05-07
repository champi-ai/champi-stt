"""Integration tests for full assistant workflow."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from champi_stt.assistant.commands import CommandRegistry
from champi_stt.assistant.service import AssistantConfig, AssistantService
from champi_stt.assistant.wakeword import WakeWordEvent
from champi_stt.core.response import STTResponse


@pytest.mark.integration
@pytest.mark.asyncio
class TestAssistantWorkflow:
    """Integration tests for complete assistant workflow."""

    async def test_wake_to_command_flow(self):
        """Test complete flow from wake word to command execution."""
        # Mock STT provider
        mock_stt = AsyncMock()
        mock_stt.initialize = AsyncMock()
        mock_stt.shutdown = AsyncMock()
        mock_stt.transcribe = AsyncMock(return_value=STTResponse(text="turn on lights"))

        # Mock wake word engine
        mock_wakeword = MagicMock()
        mock_wakeword.initialize = AsyncMock()
        mock_wakeword.shutdown = AsyncMock()
        mock_wakeword.is_active = False

        # Create command registry
        registry = CommandRegistry()
        executed_commands = []

        def light_command():
            executed_commands.append("lights_on")

        registry.register_exact("turn on lights", light_command, "Turn on the lights")

        # Create config
        config = AssistantConfig(
            continuous_mode=False,  # Run once
            enable_wake_indicator=False,  # Disable UI for testing
            enable_visualizer=False,
        )

        # Create service
        service = AssistantService(
            config=config,
            stt_provider=mock_stt,
            wakeword_engine=mock_wakeword,
            command_registry=registry,
        )

        # Simulate workflow
        try:
            # Initialize service
            await service.start()

            # Simulate wake word detection
            wake_event = WakeWordEvent(keyword="hey_jarvis", timestamp=time.time())
            await service._on_wake_word(wake_event)

            # Give time to process
            await asyncio.sleep(0.5)

            # Verify command was executed
            assert len(executed_commands) == 1
            assert executed_commands[0] == "lights_on"

        finally:
            await service.stop()

    async def test_continuous_listening_mode(self):
        """Test continuous listening mode with multiple wake words."""
        mock_stt = AsyncMock()
        mock_stt.initialize = AsyncMock()
        mock_stt.shutdown = AsyncMock()
        mock_stt.transcribe = AsyncMock(
            side_effect=[
                STTResponse(text="what time is it"),
                STTResponse(text="turn off lights"),
            ]
        )

        mock_wakeword = MagicMock()
        mock_wakeword.initialize = AsyncMock()
        mock_wakeword.shutdown = AsyncMock()
        mock_wakeword.is_active = False

        registry = CommandRegistry()
        executed_commands = []

        def time_command():
            executed_commands.append("time")

        def lights_off_command():
            executed_commands.append("lights_off")

        registry.register_exact("what time is it", time_command, "Show time")
        registry.register_exact(
            "turn off lights", lights_off_command, "Turn off lights"
        )

        config = AssistantConfig(
            continuous_mode=True,
            enable_wake_indicator=False,
            enable_visualizer=False,
        )

        service = AssistantService(
            config=config,
            stt_provider=mock_stt,
            wakeword_engine=mock_wakeword,
            command_registry=registry,
        )

        try:
            await service.start()

            # First wake word
            wake1 = WakeWordEvent(keyword="hey_jarvis", timestamp=time.time())
            await service._on_wake_word(wake1)
            await asyncio.sleep(0.3)

            # Second wake word
            wake2 = WakeWordEvent(keyword="hey_jarvis", timestamp=time.time())
            await service._on_wake_word(wake2)
            await asyncio.sleep(0.3)

            # Verify both commands executed
            assert len(executed_commands) == 2
            assert "time" in executed_commands
            assert "lights_off" in executed_commands

        finally:
            await service.stop()

    async def test_error_recovery(self):
        """Test that service recovers from errors."""
        mock_stt = AsyncMock()
        mock_stt.initialize = AsyncMock()
        mock_stt.shutdown = AsyncMock()
        mock_stt.transcribe = AsyncMock(
            side_effect=[
                Exception("STT error"),
                STTResponse(text="turn on lights"),
            ]
        )

        mock_wakeword = MagicMock()
        mock_wakeword.initialize = AsyncMock()
        mock_wakeword.shutdown = AsyncMock()
        mock_wakeword.is_active = False

        registry = CommandRegistry()
        executed_commands = []

        def light_command():
            executed_commands.append("lights_on")

        registry.register_exact("turn on lights", light_command, "Turn on lights")

        config = AssistantConfig(
            continuous_mode=True,
            enable_wake_indicator=False,
            enable_visualizer=False,
        )

        service = AssistantService(
            config=config,
            stt_provider=mock_stt,
            wakeword_engine=mock_wakeword,
            command_registry=registry,
        )

        try:
            await service.start()

            # First wake (will error)
            wake1 = WakeWordEvent(keyword="hey_jarvis", timestamp=time.time())
            await service._on_wake_word(wake1)
            await asyncio.sleep(0.3)

            # Second wake (should succeed)
            wake2 = WakeWordEvent(keyword="hey_jarvis", timestamp=time.time())
            await service._on_wake_word(wake2)
            await asyncio.sleep(0.3)

            # Verify service recovered and executed second command
            assert len(executed_commands) == 1
            assert executed_commands[0] == "lights_on"

        finally:
            await service.stop()


@pytest.mark.integration
@pytest.mark.asyncio
class TestCommandExecution:
    """Integration tests for command execution."""

    async def test_exact_command_matching(self):
        """Test exact command matching."""
        registry = CommandRegistry()
        results = []

        registry.register_exact("lights on", lambda: results.append("on"), "Lights on")
        registry.register_exact(
            "lights off", lambda: results.append("off"), "Lights off"
        )

        # Execute exact matches
        match1 = registry.find_command("lights on")
        assert match1 is not None
        match1.handler()

        match2 = registry.find_command("lights off")
        assert match2 is not None
        match2.handler()

        assert results == ["on", "off"]

    async def test_pattern_command_matching(self):
        """Test pattern-based command matching with parameters."""
        registry = CommandRegistry()
        results = []

        def set_volume(level: str):
            results.append(f"volume_{level}")

        registry.register_pattern(
            r"set volume to (?P<level>\d+)", set_volume, "Set volume level"
        )

        # Execute pattern match
        match = registry.find_command("set volume to 50")
        assert match is not None
        match.handler(**match.params)

        assert results == ["volume_50"]

    async def test_unknown_command_handling(self):
        """Test handling of unknown commands."""
        registry = CommandRegistry()

        match = registry.find_command("unknown command")
        assert match is None
