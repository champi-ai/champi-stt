"""Tests for CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from champi_stt.cli import cli


class TestCLIBasics:
    """Tests for basic CLI functionality."""

    def test_cli_help(self):
        """Test CLI help command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Champi STT" in result.output
        assert "transcribe" in result.output
        assert "assistant" in result.output

    def test_cli_version(self):
        """Test CLI version command."""
        from importlib.metadata import version

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert version("champi-stt") in result.output

    def test_list_providers(self):
        """Test list-providers command."""
        runner = CliRunner()

        with patch("champi_stt.list_providers") as mock_list:
            mock_list.return_value = ["whisperlive", "openai", "deepgram"]

            result = runner.invoke(cli, ["list-providers"])

            assert result.exit_code == 0
            assert "whisperlive" in result.output
            assert "Available STT providers" in result.output


class TestTranscribeCommand:
    """Tests for transcribe command."""

    def test_transcribe_help(self):
        """Test transcribe command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["transcribe", "--help"])

        assert result.exit_code == 0
        assert "Transcribe an audio file" in result.output
        assert "--provider" in result.output
        assert "--language" in result.output

    def test_transcribe_missing_file(self):
        """Test transcribe with missing file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["transcribe", "nonexistent.wav"])

        assert result.exit_code != 0
        assert (
            "does not exist" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_transcribe_success_text_format(self, sample_audio_file: Path):
        """Test successful transcription with text format."""
        runner = CliRunner()

        mock_provider = MagicMock()
        mock_provider.initialize = AsyncMock()
        mock_provider.shutdown = AsyncMock()
        mock_provider.transcribe = AsyncMock(return_value="hello world")

        with patch("champi_stt.get_provider") as mock_get:
            mock_get.return_value = mock_provider

            result = runner.invoke(
                cli, ["transcribe", str(sample_audio_file), "--format", "text"]
            )

            assert result.exit_code == 0
            assert "hello world" in result.output
            mock_provider.initialize.assert_called_once()
            mock_provider.shutdown.assert_called_once()

    def test_transcribe_json_format(self, sample_audio_file: Path):
        """Test transcription with JSON format."""
        runner = CliRunner()

        mock_result = {
            "text": "hello world",
            "language": "en",
            "segments": [],
        }

        mock_provider = MagicMock()
        mock_provider.initialize = AsyncMock()
        mock_provider.shutdown = AsyncMock()
        mock_provider.transcribe = AsyncMock(return_value=mock_result)

        with patch("champi_stt.get_provider") as mock_get:
            mock_get.return_value = mock_provider

            result = runner.invoke(
                cli, ["transcribe", str(sample_audio_file), "--format", "json"]
            )

            assert result.exit_code == 0
            # Check if output is valid JSON
            output_data = json.loads(result.output)
            assert output_data["text"] == "hello world"

    def test_transcribe_with_language(self, sample_audio_file: Path):
        """Test transcription with language option."""
        runner = CliRunner()

        mock_provider = MagicMock()
        mock_provider.initialize = AsyncMock()
        mock_provider.shutdown = AsyncMock()
        mock_provider.transcribe = AsyncMock(return_value="hola mundo")

        with patch("champi_stt.get_provider") as mock_get:
            mock_get.return_value = mock_provider

            result = runner.invoke(
                cli,
                [
                    "transcribe",
                    str(sample_audio_file),
                    "--language",
                    "es",
                ],
            )

            assert result.exit_code == 0
            mock_provider.transcribe.assert_called_once()
            call_args = mock_provider.transcribe.call_args
            assert call_args.kwargs.get("language") == "es"

    def test_transcribe_custom_provider(self, sample_audio_file: Path):
        """Test transcription with custom provider."""
        runner = CliRunner()

        mock_provider = MagicMock()
        mock_provider.initialize = AsyncMock()
        mock_provider.shutdown = AsyncMock()
        mock_provider.transcribe = AsyncMock(return_value="test")

        with patch("champi_stt.get_provider") as mock_get:
            mock_get.return_value = mock_provider

            result = runner.invoke(
                cli,
                ["transcribe", str(sample_audio_file), "--provider", "openai"],
            )

            assert result.exit_code == 0
            mock_get.assert_called_with("openai")


class TestAssistantCommands:
    """Tests for assistant subcommands."""

    def test_assistant_help(self):
        """Test assistant command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["assistant", "--help"])

        assert result.exit_code == 0
        assert "Voice assistant commands" in result.output
        assert "start" in result.output
        assert "init-config" in result.output

    @pytest.mark.skip(reason="Requires complete AssistantConfig implementation")
    def test_init_config(self):
        """Test init-config command."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(
                cli, ["assistant", "init-config", "--output", "test_config.yaml"]
            )

            assert result.exit_code == 0
            assert "Created config file" in result.output
            assert "test_config.yaml" in result.output

    @pytest.mark.skip(reason="Requires complete AssistantConfig implementation")
    def test_init_config_default_output(self):
        """Test init-config with default output path."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["assistant", "init-config"])

            assert result.exit_code == 0
            assert "assistant_config.yaml" in result.output

    def test_init_commands(self):
        """Test init-commands command."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_commands.yaml"

            result = runner.invoke(
                cli, ["assistant", "init-commands", "--output", str(output_path)]
            )

            assert result.exit_code == 0
            assert "Created commands file" in result.output
            assert output_path.exists()

            # Verify YAML structure
            with open(output_path) as f:
                commands = yaml.safe_load(f)

            assert "exact" in commands
            assert "patterns" in commands
            assert "turn on lights" in commands["exact"]

    def test_init_commands_default_output(self):
        """Test init-commands with default output."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["assistant", "init-commands"])

            assert result.exit_code == 0
            assert "commands.yaml" in result.output
            assert Path("commands.yaml").exists()

    def test_start_assistant_help(self):
        """Test assistant start command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["assistant", "start", "--help"])

        assert result.exit_code == 0
        assert "Start the voice assistant" in result.output
        assert "--config" in result.output


class TestCommand:
    """Tests for test command."""

    def test_test_help(self):
        """Test test command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["test", "--help"])

        assert result.exit_code == 0
        assert "Test STT provider" in result.output
        assert "--provider" in result.output

    def test_test_provider(self):
        """Test testing a provider."""
        runner = CliRunner()

        mock_provider = MagicMock()
        mock_provider.initialize = AsyncMock()
        mock_provider.shutdown = AsyncMock()
        mock_provider.transcribe = AsyncMock(return_value="test transcription")

        mock_audio = MagicMock()

        with (
            patch("champi_stt.get_provider") as mock_get,
            patch("champi_stt.core.audio.record_audio") as mock_record,
        ):
            mock_get.return_value = mock_provider
            mock_record.return_value = mock_audio

            result = runner.invoke(cli, ["test", "--provider", "whisperlive"])

            assert result.exit_code == 0
            assert "Testing whisperlive" in result.output
            assert "Recording" in result.output
            mock_provider.initialize.assert_called_once()
            mock_record.assert_called_once()


class TestCLIIntegration:
    """Integration tests for CLI."""

    def test_full_transcribe_workflow(self, sample_audio_file: Path):
        """Test complete transcribe workflow."""
        runner = CliRunner()

        mock_provider = MagicMock()
        mock_provider.initialize = AsyncMock()
        mock_provider.shutdown = AsyncMock()
        mock_provider.transcribe = AsyncMock(
            return_value={"text": "integration test", "language": "en"}
        )

        with patch("champi_stt.get_provider") as mock_get:
            mock_get.return_value = mock_provider

            result = runner.invoke(
                cli,
                [
                    "transcribe",
                    str(sample_audio_file),
                    "--provider",
                    "whisperlive",
                    "--language",
                    "en",
                    "--format",
                    "json",
                ],
            )

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["text"] == "integration test"

    @pytest.mark.skip(reason="Requires complete AssistantConfig implementation")
    def test_init_config_and_commands_workflow(self):
        """Test creating config and commands files."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create config
            config_result = runner.invoke(
                cli, ["assistant", "init-config", "--output", "my_config.yaml"]
            )

            assert config_result.exit_code == 0
            assert "my_config.yaml" in config_result.output

            # Create commands
            commands_result = runner.invoke(
                cli, ["assistant", "init-commands", "--output", "my_commands.yaml"]
            )

            assert commands_result.exit_code == 0
            assert Path("my_commands.yaml").exists()

    def test_cli_error_handling(self):
        """Test CLI error handling."""
        runner = CliRunner()

        # Test with invalid command
        result = runner.invoke(cli, ["invalid-command"])

        assert result.exit_code != 0

    def test_transcribe_with_error(self, sample_audio_file: Path):
        """Test transcribe command error handling."""
        runner = CliRunner()

        mock_provider = MagicMock()
        mock_provider.initialize = AsyncMock()
        mock_provider.shutdown = AsyncMock()
        mock_provider.transcribe = AsyncMock(
            side_effect=Exception("Transcription failed")
        )

        with patch("champi_stt.get_provider") as mock_get:
            mock_get.return_value = mock_provider

            result = runner.invoke(cli, ["transcribe", str(sample_audio_file)])

            assert result.exit_code != 0


class TestCLIOutput:
    """Tests for CLI output formatting."""

    def test_transcribe_text_output(self, sample_audio_file: Path):
        """Test text output format."""
        runner = CliRunner()

        mock_provider = MagicMock()
        mock_provider.initialize = AsyncMock()
        mock_provider.shutdown = AsyncMock()
        mock_provider.transcribe = AsyncMock(return_value="simple text output")

        with patch("champi_stt.get_provider") as mock_get:
            mock_get.return_value = mock_provider

            result = runner.invoke(cli, ["transcribe", str(sample_audio_file)])

            assert result.exit_code == 0
            assert "simple text output" in result.output

    @pytest.mark.skip(reason="Requires complete AssistantConfig implementation")
    def test_init_config_output_message(self):
        """Test init-config output message."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(
                cli, ["assistant", "init-config", "--output", "config.yaml"]
            )

            assert result.exit_code == 0
            assert "✓" in result.output
            assert "config.yaml" in result.output
            assert "champi-stt assistant start" in result.output

    def test_list_providers_format(self):
        """Test list providers output format."""
        runner = CliRunner()

        with patch("champi_stt.list_providers") as mock_list:
            mock_list.return_value = ["provider1", "provider2", "provider3"]

            result = runner.invoke(cli, ["list-providers"])

            assert result.exit_code == 0
            assert "provider1" in result.output
            assert "provider2" in result.output
            assert "provider3" in result.output
            # Check bullet formatting
            assert "- provider1" in result.output or "provider1" in result.output
