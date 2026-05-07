"""
Voice Assistant Features
=========================

Complete voice assistant implementation with wake word detection, STT integration,
command execution, and visual feedback via IPC-based UI.

Features
--------
- **Wake Word Detection**: OpenWakeWord (default), Whisper, Vosk
- **Speech-to-Text**: Multi-provider support (WhisperLive, OpenAI, Deepgram)
- **Command System**: Exact matching and regex patterns with parameter extraction
- **Speaker Identification**: Voice embeddings using Resemblyzer
- **Visual Feedback**: IPC-based wake indicator UI with GLFW/ImGui
- **IPC System**: Low-latency shared memory communication (<1ms)

Quick Start
-----------
**1. Create configuration**::

    champi-stt assistant init-config

**2. Start assistant**::

    champi-stt assistant start --config assistant_config.yaml

**3. Speak wake word** (default: "hey_jarvis"):
   - Visual indicator shows state (idle → awake → recording → transcribing → executing)
   - Speak command after wake word
   - Assistant executes matched command

Architecture
------------
The assistant consists of several integrated components:

1. **Service Daemon** (champi_stt.assistant.service):
   - Coordinates wake word detection, STT, and command execution
   - Manages continuous listening mode
   - Emits IPC signals for UI updates

2. **Wake Word Detection** (champi_stt.assistant.wakeword):
   - Monitors audio stream for wake words
   - Triggers recording on detection
   - Supports multiple wake word engines

3. **Command System** (champi_stt.assistant.commands):
   - CommandRegistry: Stores exact and pattern-based commands
   - CommandExecutor: Executes matched commands
   - CommandParser: Parses YAML configuration

4. **Speaker Identification** (champi_stt.assistant.speaker):
   - Creates voice embeddings using Resemblyzer
   - Matches speakers based on cosine similarity
   - Enrollment via CLI: `champi-stt speaker enroll <name>`

5. **IPC System** (champi_stt.assistant.ipc):
   - Real-time signal communication
   - Binary struct-based for low latency
   - Shared memory regions per signal type

Example Usage
-------------
**Programmatic usage**::

    from champi_stt import get_provider
    from champi_stt.assistant.service import AssistantConfig, AssistantService
    from champi_stt.assistant.wakeword import WakeWordConfig, WhisperWakeWordDetector
    from champi_stt.assistant.commands import CommandRegistry

    # Setup STT
    stt = get_provider("whisperlive")
    await stt.initialize()

    # Setup wake word
    wakeword_config = WakeWordConfig(keywords=["hey_jarvis"])
    wakeword = WhisperWakeWordDetector(wakeword_config, stt)

    # Setup commands
    registry = CommandRegistry()
    registry.register_exact("turn on lights", lambda: print("Lights on!"))

    # Create and start service
    config = AssistantConfig()
    service = AssistantService(config, stt, wakeword, registry)
    await service.start()

**Custom commands via YAML**::

    exact:
      "turn on lights":
        type: "api"
        url: "http://192.168.1.100/api/lights/on"
        method: "POST"

    patterns:
      "set volume to (?P<level>\\d+)":
        type: "shell"
        command: "pactl set-sink-volume @DEFAULT_SINK@ {level}%"

CLI Commands
------------
- `champi-stt assistant start`: Start assistant service
- `champi-stt assistant init-config`: Create config file
- `champi-stt speaker enroll <name>`: Enroll speaker
- `champi-stt speaker list`: List enrolled speakers
- `champi-stt ipc cleanup`: Clean orphaned IPC regions
- `champi-stt ipc status`: Show IPC memory status
- `champi-stt ipc test-ui`: Launch UI standalone

Configuration
-------------
See `examples/assistant_config.yaml` for full configuration options.

Key settings:
- `wakeword.engine`: "openwakeword" | "whisper" | "vosk"
- `wakeword.keywords`: List of wake words
- `stt.provider`: "whisperlive" | "openai" | "deepgram"
- `commands.file`: Path to commands YAML
- `ipc.memory_prefix`: Namespace for IPC

See Also
--------
- ARCHITECTURE.md: System architecture
- docs/IPC.md: IPC documentation
- CONTRIBUTING.md: Development guide
"""

from champi_stt.assistant.ipc import (
    AssistantSharedMemoryManager,
    AssistantSignalManager,
    AssistantSignalProcessor,
    AssistantSignalType,
)
from champi_stt.assistant.speaker import SpeakerIdentifier, SpeakerProfile

__all__ = [
    "AssistantSharedMemoryManager",
    "AssistantSignalManager",
    "AssistantSignalProcessor",
    "AssistantSignalType",
    "SpeakerIdentifier",
    "SpeakerProfile",
]
