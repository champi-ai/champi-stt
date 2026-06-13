"""Tests for command registry."""

import pytest

from champi_stt.assistant.commands.registry import CommandRegistry


@pytest.fixture
def registry():
    return CommandRegistry()


class TestCommandRegistry:
    def test_register_exact(self, registry):
        registry.register_exact("turn on lights", lambda: "ok")
        assert "turn on lights" in registry._exact_commands

    def test_register_exact_case_normalization(self, registry):
        registry.register_exact("TURN ON LIGHTS", lambda: "ok")
        assert "turn on lights" in registry._exact_commands

    def test_register_exact_overwrite(self, registry):
        registry.register_exact("hello", lambda: "a")
        registry.register_exact("hello", lambda: "b")
        assert len(registry._exact_commands) == 1

    def test_register_pattern(self, registry):
        registry.register_pattern(r"set volume to (?P<level>\d+)", lambda level: level)
        assert len(registry._pattern_commands) == 1

    def test_len(self, registry):
        registry.register_exact("cmd1", lambda: None)
        registry.register_exact("cmd2", lambda: None)
        registry.register_pattern(r"do (?P<x>\w+)", lambda x: x)
        assert len(registry) == 3

    def test_clear(self, registry):
        registry.register_exact("hello", lambda: None)
        registry.clear()
        assert len(registry) == 0

    @pytest.mark.asyncio
    async def test_execute_exact_match(self, registry):
        async def handler():
            return "lights on"

        registry.register_exact("turn on lights", handler)
        result = await registry.execute("turn on lights")
        assert result == "lights on"

    @pytest.mark.asyncio
    async def test_execute_case_insensitive(self, registry):
        async def handler():
            return "ok"

        registry.register_exact("hello", handler)
        result = await registry.execute("HELLO")
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_execute_pattern_match(self, registry):
        async def set_vol(level: str):
            return f"volume={level}"

        registry.register_pattern(r"set volume to (?P<level>\d+)", set_vol)
        result = await registry.execute("set volume to 50")
        assert result == "volume=50"

    @pytest.mark.asyncio
    async def test_execute_no_match_returns_none(self, registry):
        result = await registry.execute("completely unknown xyz abc")
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_sync_handler(self, registry):
        def sync_handler():
            return "sync result"

        registry.register_exact("sync cmd", sync_handler)
        result = await registry.execute("sync cmd")
        assert result == "sync result"

    def test_list_commands(self, registry):
        registry.register_exact("hello", lambda: None, "Say hello")
        registry.register_pattern(r"search (?P<q>.+)", lambda q: q, "Search")
        commands = registry.list_commands()
        assert len(commands) == 2
        types = {c["type"] for c in commands}
        assert "exact" in types
        assert "pattern" in types

    def test_unregister_exact(self, registry):
        registry.register_exact("bye", lambda: None)
        removed = registry.unregister("bye")
        assert removed is True
        assert "bye" not in registry._exact_commands

    def test_unregister_not_found(self, registry):
        removed = registry.unregister("nonexistent")
        assert removed is False

    def test_unregister_pattern(self, registry):
        pattern = r"do (?P<x>\w+)"
        registry.register_pattern(pattern, lambda x: x)
        removed = registry.unregister(pattern)
        assert removed is True
        assert len(registry._pattern_commands) == 0

    @pytest.mark.asyncio
    async def test_handler_exception_propagates(self, registry):
        async def bad_handler():
            raise RuntimeError("boom")

        registry.register_exact("fail", bad_handler)
        with pytest.raises(RuntimeError, match="boom"):
            await registry.execute("fail")
