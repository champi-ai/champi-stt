"""
CLI for champi-stt voice assistant
"""

import asyncio
import sys

import click

from champi_stt.core.logging import configure_logging


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Champi STT - Multi-Provider Speech-to-Text Voice Assistant"""
    pass


@cli.command()
@click.argument("audio_file", type=click.Path(exists=True))
@click.option("--provider", default="whisperlive", help="STT provider to use")
@click.option("--language", default=None, help="Language code (e.g., 'en')")
@click.option(
    "--format",
    "response_format",
    default="text",
    help="Output format (text/json/verbose_json)",
)
def transcribe(audio_file, provider, language, response_format):
    """Transcribe an audio file"""
    from champi_stt import get_provider

    async def run():
        stt = get_provider(provider)
        await stt.initialize()

        result = await stt.transcribe(
            audio_file, language=language, response_format=response_format
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
    from champi_stt import get_provider
    from champi_stt.assistant.commands import (
        CommandExecutor,
        CommandParser,
        CommandRegistry,
    )
    from champi_stt.assistant.commands.builtin import register_builtin_commands
    from champi_stt.assistant.service import AssistantConfig, AssistantService
    from champi_stt.assistant.wakeword import WakeWordConfig, WhisperWakeWordDetector

    async def run():
        # Load config
        if config:
            assistant_config = AssistantConfig.from_file(config)
        else:
            assistant_config = AssistantConfig.from_env()

        # Setup logging with config level
        configure_logging(
            level=assistant_config.log_level, log_file=assistant_config.log_file
        )

        click.echo("Starting voice assistant with config:")
        click.echo(f"  STT Provider: {assistant_config.stt_provider}")
        click.echo(f"  Wake Words: {assistant_config.wakeword_keywords}")
        click.echo(f"  Wake Engine: {assistant_config.wakeword_engine}")

        # Setup STT provider
        stt = get_provider(assistant_config.stt_provider, **assistant_config.stt_config)

        # Setup wake word engine
        wakeword_config = WakeWordConfig(
            keywords=assistant_config.wakeword_keywords,
            sensitivity=assistant_config.wakeword_sensitivity,
        )

        # Choose wake word engine based on config
        # Note: OpenWakeWord implementation pending, using Whisper as default
        if assistant_config.wakeword_engine == "openwakeword":
            click.echo("⚠️  OpenWakeWord not yet implemented, falling back to Whisper")
            wakeword = WhisperWakeWordDetector(wakeword_config, stt)
        else:
            # Default to Whisper
            wakeword = WhisperWakeWordDetector(wakeword_config, stt)

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
        service = AssistantService(
            assistant_config,
            stt,
            wakeword,
            registry,
            enable_visualizer=assistant_config.enable_visualizer,
        )

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
@click.option(
    "--output",
    type=click.Path(),
    default="assistant_config.yaml",
    help="Output file path",
)
def init_config(output):
    """Create default assistant configuration file"""
    from champi_stt.assistant.service import AssistantConfig
    from champi_stt.core.audio import list_input_devices

    # Get available input devices
    try:
        devices = list_input_devices()

        if not devices:
            click.echo("No input devices found, using default device")
            selected_device = None
        else:
            click.echo("\nAvailable audio input devices:")
            for i, device in enumerate(devices):
                click.echo(
                    f"  [{i}] {device['name']} ({device['sample_rate']} Hz, {device['channels']} ch)"
                )

            click.echo("  [d] Use default device")

            choice = click.prompt(
                "\nSelect device number (or 'd' for default)",
                type=str,
                default="d",
                show_default=True,
            )

            if choice.lower() == "d":
                selected_device = None
            else:
                try:
                    idx = int(choice)
                    if 0 <= idx < len(devices):
                        selected_device = devices[idx]
                    else:
                        click.echo("Invalid selection, using default device")
                        selected_device = None
                except ValueError:
                    click.echo("Invalid input, using default device")
                    selected_device = None

    except Exception as e:
        click.echo(f"Error listing devices: {e}, using default device")
        selected_device = None

    # Create config with selected device and full WhisperLive defaults
    from champi_stt.providers.whisperlive.config import WhisperLiveConfig

    config = AssistantConfig()
    if selected_device:
        config.input_device = selected_device["name"]
        click.echo(f"\n✓ Selected input device: {selected_device['name']}")
    else:
        click.echo("\n✓ Using default input device")

    # Populate stt_config with WhisperLive defaults
    whisperlive_defaults = WhisperLiveConfig()
    config.stt_config = {
        "model_size": whisperlive_defaults.model_size,
        "language": whisperlive_defaults.language,
        "task": whisperlive_defaults.task,
        "device": whisperlive_defaults.device,
        "compute_type": whisperlive_defaults.compute_type,
        "cpu_threads": whisperlive_defaults.cpu_threads,
        "vad_filter": whisperlive_defaults.vad_filter,
        "word_timestamps": whisperlive_defaults.word_timestamps,
        "audio_format": whisperlive_defaults.audio_format,
        "sample_rate": whisperlive_defaults.sample_rate,
        "disable_silence_detection": whisperlive_defaults.disable_silence_detection,
        "silence_threshold_ms": whisperlive_defaults.silence_threshold_ms,
        "min_recording_duration": whisperlive_defaults.min_recording_duration,
        "vad_aggressiveness": whisperlive_defaults.vad_aggressiveness,
        "vad_chunk_duration_ms": whisperlive_defaults.vad_chunk_duration_ms,
        "initial_silence_grace_period": whisperlive_defaults.initial_silence_grace_period,
        "beam_size": whisperlive_defaults.beam_size,
        "best_of": whisperlive_defaults.best_of,
        "temperature": whisperlive_defaults.temperature,
        "compression_ratio_threshold": whisperlive_defaults.compression_ratio_threshold,
        "log_prob_threshold": whisperlive_defaults.log_prob_threshold,
        "no_speech_threshold": whisperlive_defaults.no_speech_threshold,
        "batch_size": whisperlive_defaults.batch_size,
        "cache_dir": whisperlive_defaults.cache_dir,
        "enable_events": whisperlive_defaults.enable_events,
        "event_emit_interval": whisperlive_defaults.event_emit_interval,
        "save_transcriptions": whisperlive_defaults.save_transcriptions,
        "transcriptions_dir": whisperlive_defaults.transcriptions_dir,
        "log_level": whisperlive_defaults.log_level,
        "log_file": whisperlive_defaults.log_file,
    }

    config.save(output)

    click.echo(f"✓ Created config file: {output}")
    click.echo("\nStart the assistant with:")
    click.echo(f"  champi-stt assistant start --config {output}")


@assistant.command()
@click.option(
    "--output", type=click.Path(), default="commands.yaml", help="Output file path"
)
def init_commands(output):
    """Create example commands configuration file"""
    import yaml

    example_commands = {
        "exact": {
            "turn on lights": {
                "type": "api",
                "url": "http://192.168.1.100/api/lights/on",
                "method": "POST",
                "description": "Turn on the lights",
            },
            "turn off lights": {
                "type": "api",
                "url": "http://192.168.1.100/api/lights/off",
                "method": "POST",
                "description": "Turn off the lights",
            },
        },
        "patterns": {
            "set volume to (?P<level>\\d+)": {
                "type": "shell",
                "command": "pactl set-sink-volume @DEFAULT_SINK@ {level}%",
                "description": "Set system volume",
            },
            "search for (?P<query>.+)": {
                "type": "python",
                "function": "champi_stt.assistant.commands.builtin.web_search",
                "description": "Search the web",
            },
        },
    }

    with open(output, "w") as f:
        yaml.dump(example_commands, f, default_flow_style=False, indent=2)

    click.echo(f"✓ Created commands file: {output}")
    click.echo("\nEdit the commands and reference it in your config:")
    click.echo("  commands:")
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


@cli.group()
def speaker():
    """Speaker identification commands"""
    pass


@speaker.command()
@click.argument("name")
@click.option("--samples", default=3, help="Number of voice samples to collect")
@click.option("--duration", default=3.0, help="Duration of each sample in seconds")
def enroll(name, samples, duration):
    """Enroll a new speaker with voice samples"""
    from champi_stt.assistant.speaker import SpeakerIdentifier
    from champi_stt.core.audio import record_audio

    async def run():
        identifier = SpeakerIdentifier()

        click.echo(f"Enrolling speaker: {name}")
        click.echo(
            f"You will be asked to record {samples} voice samples ({duration}s each)"
        )

        audio_samples = []
        for i in range(samples):
            click.echo(
                f"\nSample {i + 1}/{samples} - Press Enter to start recording..."
            )
            input()

            click.echo(f"Recording for {duration} seconds... Speak now!")
            audio = await record_audio(duration=duration)

            if len(audio) == 0:
                click.echo("Warning: No audio recorded, trying again...")
                continue

            audio_samples.append(audio)
            click.echo(f"✓ Sample {i + 1} recorded")

        # Enroll speaker
        identifier.enroll_speaker(name, audio_samples)
        click.echo(f"\n✓ Speaker '{name}' enrolled successfully!")

    asyncio.run(run())


@speaker.command()
def list():
    """List enrolled speakers"""
    from champi_stt.assistant.speaker import SpeakerIdentifier

    try:
        identifier = SpeakerIdentifier()
        speakers = identifier.list_speakers()

        if speakers:
            click.echo("Enrolled speakers:")
            for speaker_name in speakers:
                click.echo(f"  - {speaker_name}")
        else:
            click.echo("No speakers enrolled yet")
    except ImportError as e:
        click.echo(f"Error: {e}")
        click.echo("Install resemblyzer: uv pip install resemblyzer")


@speaker.command()
@click.argument("name")
def remove(name):
    """Remove an enrolled speaker"""
    from champi_stt.assistant.speaker import SpeakerIdentifier

    identifier = SpeakerIdentifier()

    if name not in identifier.list_speakers():
        click.echo(f"Speaker '{name}' not found")
        return

    if click.confirm(f"Remove speaker '{name}'?"):
        identifier.remove_speaker(name)
        click.echo(f"✓ Speaker '{name}' removed")
    else:
        click.echo("Cancelled")


@cli.group()
def ipc():
    """IPC (Inter-Process Communication) management commands"""
    pass


@ipc.command()
@click.option("--prefix", default="champi_assistant", help="Memory region prefix")
def cleanup(prefix):
    """Clean up orphaned shared memory regions"""
    from champi_stt.assistant.ipc import cleanup_orphaned_regions

    click.echo(f"Cleaning up orphaned regions with prefix: {prefix}")
    cleaned = cleanup_orphaned_regions(name_prefix=prefix)

    if cleaned:
        click.echo(f"\n✓ Cleaned up {len(cleaned)} orphaned regions:")
        for region in cleaned:
            click.echo(f"  - {region}")
    else:
        click.echo("✓ No orphaned regions found")


@ipc.command()
@click.option("--prefix", default="champi_assistant", help="Memory region prefix")
def status(prefix):
    """Show status of shared memory regions"""
    from multiprocessing import shared_memory

    from champi_stt.assistant.ipc import AssistantSignalType

    click.echo(f"Checking shared memory regions with prefix: {prefix}\n")

    existing_regions = []
    missing_regions = []

    for signal_type in AssistantSignalType:
        # Check data region
        region_name = f"{prefix}_{signal_type.name.lower()}"
        try:
            shm = shared_memory.SharedMemory(name=region_name)
            existing_regions.append((region_name, shm.size))
            shm.close()
        except FileNotFoundError:
            missing_regions.append(region_name)

        # Check ACK region
        ack_region_name = f"{prefix}_{signal_type.name.lower()}_ack"
        try:
            ack_shm = shared_memory.SharedMemory(name=ack_region_name)
            existing_regions.append((ack_region_name, ack_shm.size))
            ack_shm.close()
        except FileNotFoundError:
            missing_regions.append(ack_region_name)

    if existing_regions:
        click.echo("📍 Existing regions:")
        for name, size in existing_regions:
            click.echo(f"  ✓ {name} ({size} bytes)")

    if missing_regions:
        click.echo(f"\n❌ Missing regions ({len(missing_regions)}):")
        for name in missing_regions:
            click.echo(f"  ✗ {name}")

    if not existing_regions and not missing_regions:
        click.echo("No regions configured")


@ipc.command()
@click.option("--prefix", default="champi_assistant", help="Memory region prefix")
def test_ui(prefix):
    """Launch wake indicator UI for testing (standalone mode)"""
    from champi_stt.assistant.ui.wake_indicator_ui import wake_indicator_main

    click.echo(f"Launching wake indicator UI with prefix: {prefix}")
    click.echo("Right-click on the indicator to test different states\n")

    try:
        wake_indicator_main(name_prefix=prefix)
    except KeyboardInterrupt:
        click.echo("\n✓ UI closed")
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@cli.group()
def service():
    """Manage the champi-stt system service."""


@service.command("install")
@click.option("--config", default=None, help="Path to assistant_config.yaml")
@click.option("--type", "service_type", default="systemd",
              type=click.Choice(["systemd", "launchd"]), show_default=True,
              help="Service manager type")
@click.option("--no-enable", is_flag=True, default=False, help="Skip systemctl enable (systemd only)")
@click.option("--no-start", is_flag=True, default=False, help="Skip start after install")
def service_install(config, service_type, no_enable, no_start):
    """Install champi-stt as a system service."""
    try:
        if service_type == "systemd":
            from champi_stt.assistant.service.systemd.installer import install
            path = install(config=config, enable=not no_enable, start=not no_start)
        else:
            from champi_stt.assistant.service.launchd.installer import install
            path = install(config=config, load=not no_start)
        click.echo(f"Service installed: {path}")
        if not no_start:
            click.echo("Service started. Check status with: champi-stt service status")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@service.command("uninstall")
@click.option("--type", "service_type", default="systemd",
              type=click.Choice(["systemd", "launchd"]), show_default=True)
def service_uninstall(service_type):
    """Remove the champi-stt system service."""
    try:
        if service_type == "systemd":
            from champi_stt.assistant.service.systemd.installer import uninstall
        else:
            from champi_stt.assistant.service.launchd.installer import uninstall
        uninstall()
        click.echo("Service uninstalled.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@service.command("status")
@click.option("--type", "service_type", default="systemd",
              type=click.Choice(["systemd", "launchd"]), show_default=True)
def service_status(service_type):
    """Show the status of the champi-stt service."""
    if service_type == "systemd":
        from champi_stt.assistant.service.systemd.installer import status
    else:
        from champi_stt.assistant.service.launchd.installer import status
    click.echo(status())


if __name__ == "__main__":
    cli()
