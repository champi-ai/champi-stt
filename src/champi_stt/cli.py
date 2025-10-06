"""
CLI for champi-stt voice assistant
"""

import asyncio
import click
import logging
import sys
from pathlib import Path


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Champi STT - Multi-Provider Speech-to-Text Voice Assistant"""
    pass


@cli.command()
@click.argument("audio_file", type=click.Path(exists=True))
@click.option("--provider", default="whisperlive", help="STT provider to use")
@click.option("--language", default=None, help="Language code (e.g., 'en')")
@click.option("--format", "response_format", default="text", help="Output format (text/json/verbose_json)")
def transcribe(audio_file, provider, language, response_format):
    """Transcribe an audio file"""
    from champi_stt import get_provider

    async def run():
        stt = get_provider(provider)
        await stt.initialize()

        result = await stt.transcribe(
            audio_file,
            language=language,
            response_format=response_format
        )

        if isinstance(result, dict):
            import json
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(result)

        await stt.shutdown()

    asyncio.run(run())


@cli.group()
def assistant():
    """Voice assistant commands"""
    pass


@assistant.command()
@click.option("--config", type=click.Path(), help="Config file path")
def start(config):
    """Start the voice assistant service"""
    from champi_stt.assistant.service import AssistantConfig, AssistantService
    from champi_stt.assistant.wakeword import WakeWordConfig
    from champi_stt.assistant.wakeword.porcupine import PorcupineWakeWord
    from champi_stt.assistant.commands import CommandRegistry, CommandExecutor, CommandParser
    from champi_stt.assistant.commands.builtin import register_builtin_commands
    from champi_stt import get_provider

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    async def run():
        # Load config
        if config:
            assistant_config = AssistantConfig.from_file(config)
        else:
            assistant_config = AssistantConfig.from_env()

        click.echo(f"Starting voice assistant with config:")
        click.echo(f"  STT Provider: {assistant_config.stt_provider}")
        click.echo(f"  Wake Words: {assistant_config.wakeword_keywords}")

        # Setup STT provider
        stt = get_provider(
            assistant_config.stt_provider,
            **assistant_config.stt_config
        )

        # Setup wake word engine
        wakeword_config = WakeWordConfig(
            keywords=assistant_config.wakeword_keywords,
            sensitivity=assistant_config.wakeword_sensitivity,
            access_key=assistant_config.wakeword_access_key
        )
        wakeword = PorcupineWakeWord(wakeword_config)

        # Setup command system
        registry = CommandRegistry()
        executor = CommandExecutor()
        parser = CommandParser(registry, executor)

        # Load built-in commands
        if assistant_config.enable_builtin_commands:
            register_builtin_commands(registry)

        # Load custom commands from file
        if assistant_config.commands_file:
            await parser.load_from_file(assistant_config.commands_file)

        click.echo(f"  Commands Loaded: {len(registry)}")

        # Create and start service
        service = AssistantService(assistant_config, stt, wakeword, registry)

        try:
            await service.start()
        except KeyboardInterrupt:
            click.echo("\nShutting down...")
            await service.stop()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\nInterrupted")
        sys.exit(0)


@assistant.command()
@click.option("--output", type=click.Path(), default="assistant_config.yaml", help="Output file path")
def init_config(output):
    """Create default assistant configuration file"""
    from champi_stt.assistant.service import AssistantConfig

    config = AssistantConfig()
    config.save(output)

    click.echo(f"✓ Created config file: {output}")
    click.echo(f"\nEdit the config file and then start the assistant with:")
    click.echo(f"  champi-stt assistant start --config {output}")


@assistant.command()
@click.option("--output", type=click.Path(), default="commands.yaml", help="Output file path")
def init_commands(output):
    """Create example commands configuration file"""
    import yaml

    example_commands = {
        "exact": {
            "turn on lights": {
                "type": "api",
                "url": "http://192.168.1.100/api/lights/on",
                "method": "POST",
                "description": "Turn on the lights"
            },
            "turn off lights": {
                "type": "api",
                "url": "http://192.168.1.100/api/lights/off",
                "method": "POST",
                "description": "Turn off the lights"
            },
        },
        "patterns": {
            "set volume to (?P<level>\\d+)": {
                "type": "shell",
                "command": "pactl set-sink-volume @DEFAULT_SINK@ {level}%",
                "description": "Set system volume"
            },
            "search for (?P<query>.+)": {
                "type": "python",
                "function": "champi_stt.assistant.commands.builtin.web_search",
                "description": "Search the web"
            },
        }
    }

    with open(output, "w") as f:
        yaml.dump(example_commands, f, default_flow_style=False, indent=2)

    click.echo(f"✓ Created commands file: {output}")
    click.echo(f"\nEdit the commands and reference it in your config:")
    click.echo(f"  commands:")
    click.echo(f"    file: {output}")


@cli.command()
@click.option("--provider", default="whisperlive", help="STT provider to test")
def test(provider):
    """Test STT provider with microphone"""
    from champi_stt import get_provider
    from champi_stt.core.audio import record_audio

    async def run():
        click.echo(f"Testing {provider} provider...")

        stt = get_provider(provider)
        await stt.initialize()

        click.echo("\nRecording for 5 seconds...")
        audio = await record_audio(duration=5.0)

        click.echo("Transcribing...")
        result = await stt.transcribe(audio)

        text = result if isinstance(result, str) else result.get("text", "")
        click.echo(f"\nTranscription: {text}")

        await stt.shutdown()

    asyncio.run(run())


@cli.command()
def list_providers():
    """List available STT providers"""
    from champi_stt import list_providers

    providers = list_providers()

    click.echo("Available STT providers:")
    for provider in providers:
        click.echo(f"  - {provider}")


if __name__ == "__main__":
    cli()
