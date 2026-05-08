"""Tests for command parser."""

import json

import pytest
import yaml

from champi_stt.assistant.commands.executor import CommandExecutor
from champi_stt.assistant.commands.parser import CommandParser
from champi_stt.assistant.commands.registry import CommandRegistry


@pytest.fixture
def registry():
    return CommandRegistry()


@pytest.fixture
def executor():
    return CommandExecutor()


@pytest.fixture
def parser(registry, executor):
    return CommandParser(registry, executor)


class TestLoadFromDict:
    @pytest.mark.asyncio
    async def test_load_shell_exact(self, parser, registry):
        config = {
            "exact": {
                "turn on lights": {
                    "type": "shell",
                    "command": "echo lights_on",
                }
            }
        }
        count = await parser.load_from_dict(config)
        assert count == 1
        assert "turn on lights" in registry._exact_commands

    @pytest.mark.asyncio
    async def test_load_python_exact(self, parser, registry):
        config = {
            "exact": {
                "get time": {
                    "type": "python",
                    "function": "asyncio.sleep",
                    "args": [],
                }
            }
        }
        count = await parser.load_from_dict(config)
        assert count == 1

    @pytest.mark.asyncio
    async def test_load_api_pattern(self, parser, registry):
        config = {
            "patterns": {
                r"search (?P<q>.+)": {
                    "type": "api",
                    "url": "https://api.example.com/search?q={q}",
                    "method": "GET",
                }
            }
        }
        count = await parser.load_from_dict(config)
        assert count == 1
        assert len(registry._pattern_commands) == 1

    @pytest.mark.asyncio
    async def test_load_empty_config(self, parser, registry):
        count = await parser.load_from_dict({})
        assert count == 0
        assert len(registry) == 0

    @pytest.mark.asyncio
    async def test_load_with_description(self, parser, registry):
        config = {
            "exact": {
                "hello": {
                    "type": "shell",
                    "command": "echo hello",
                    "description": "Say hello",
                }
            }
        }
        await parser.load_from_dict(config)
        cmd = registry._exact_commands["hello"]
        assert cmd.description == "Say hello"


class TestLoadFromFile:
    @pytest.mark.asyncio
    async def test_load_yaml_file(self, tmp_path, parser, registry):
        config = {
            "exact": {
                "yaml cmd": {"type": "shell", "command": "echo yaml"}
            }
        }
        config_file = tmp_path / "commands.yaml"
        config_file.write_text(yaml.dump(config))

        count = await parser.load_from_file(config_file)
        assert count == 1

    @pytest.mark.asyncio
    async def test_load_json_file(self, tmp_path, parser, registry):
        config = {
            "exact": {
                "json cmd": {"type": "shell", "command": "echo json"}
            }
        }
        config_file = tmp_path / "commands.json"
        config_file.write_text(json.dumps(config))

        count = await parser.load_from_file(config_file)
        assert count == 1

    @pytest.mark.asyncio
    async def test_missing_file_raises(self, parser, tmp_path):
        with pytest.raises(FileNotFoundError):
            await parser.load_from_file(tmp_path / "nonexistent.yaml")

    @pytest.mark.asyncio
    async def test_unsupported_format_raises(self, tmp_path, parser):
        config_file = tmp_path / "commands.txt"
        config_file.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported"):
            await parser.load_from_file(config_file)


class TestCreateHandler:
    def test_shell_handler_created(self, parser):
        handler = parser._create_handler({"type": "shell", "command": "echo hi"})
        assert callable(handler)

    def test_api_handler_created(self, parser):
        handler = parser._create_handler({
            "type": "api",
            "url": "https://example.com",
            "method": "GET",
        })
        assert callable(handler)

    def test_python_handler_created(self, parser):
        handler = parser._create_handler({
            "type": "python",
            "function": "asyncio.sleep",
        })
        assert callable(handler)

    def test_unknown_type_raises(self, parser):
        with pytest.raises(ValueError):
            parser._create_handler({"type": "unknown"})
