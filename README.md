# Champi STT

[![CI](https://github.com/divagnz/champi-stt/workflows/CI/badge.svg)](https://github.com/divagnz/champi-stt/actions)
[![Pre-commit](https://github.com/divagnz/champi-stt/workflows/Pre-commit/badge.svg)](https://github.com/divagnz/champi-stt/actions)
[![PyPI version](https://badge.fury.io/py/champi-stt.svg)](https://badge.fury.io/py/champi-stt)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Multi-Provider Speech-to-Text Library with Voice Assistant Features**

A modular, extensible Python library for speech-to-text processing with support for multiple backends and full voice assistant capabilities including wake word detection and custom voice commands.

---

## ✨ Features

### 🎤 **Multi-Provider STT Support**
- **WhisperLive** (Local, faster-whisper backend) - ✅ Implemented
- **OpenAI Whisper API** - 🔜 Coming Soon
- **Deepgram** - 🔜 Coming Soon
- Unified interface across all providers

### 🔊 **Wake Word Detection**
- **WhisperWakeWordDetector** (default, uses WhisperLive STT)
  - Continuous transcription-based detection
  - Natural language wake phrase support
  - Detects wake words in transcribed text
  - Highly flexible - any phrase can be a wake word
- Customizable sensitivity and keywords
- No API keys required
- Real-time audio streaming

### 🎯 **Voice Command System**
- Exact phrase matching
- Regex pattern matching
- Multiple action types:
  - Shell commands
  - HTTP API calls
  - Python function execution
- YAML configuration
- Built-in commands (time, web search, volume control, etc.)

### 🎨 **IPC-Based Wake Indicator**
- Real-time visual status indicator using GLFW/ImGui
- Subprocess-based UI with shared memory IPC
- Visual states:
  - **IDLE** (gray) - Waiting for wake word
  - **AWAKE** (green pulse) - Wake word detected
  - **RECORDING** (red) - Recording command
  - **TRANSCRIBING** (blue) - Processing speech
  - **EXECUTING** (yellow) - Executing command
  - **ERROR** (red flash) - Error occurred
- Binary struct-based communication for low latency
- Configurable memory namespace for isolation
- Signal loss detection with ACK tracking

### 🤖 **Voice Assistant Service**
- Continuous listening mode
- System service/daemon support
- Automatic silence detection (VAD)
- Event-driven architecture with blinker signals
- Speaker identification using voice embeddings

---

## 📦 Installation

### Basic Installation

```bash
uv pip install champi-stt
```

### Development Installation

Clone repository:
```bash
git clone https://github.com/divagnz/champi-stt.git
```

Navigate to directory:
```bash
cd champi-stt
```

Install dependencies:
```bash
uv sync --extra dev --extra all
```

---

## 🚀 Quick Start

### 1. Simple Transcription

```python
from champi_stt import get_provider

# Get default provider (WhisperLive)
provider = get_provider()
await provider.initialize()

# Transcribe audio file
result = await provider.transcribe("audio.wav")
print(result["text"])

await provider.shutdown()
```

### 2. CLI Transcription

#### Transcribe audio file
```bash
uv run champi-stt transcribe audio.wav
```

#### With custom provider and format
```bash
uv run champi-stt transcribe audio.wav --provider whisperlive --format json
```

### 3. Voice Assistant

#### Create configuration
```bash
uv run champi-stt assistant init-config --output config.yaml
```

#### Start voice assistant
```bash
uv run champi-stt assistant start --config config.yaml
```

### 4. Configuration

**Environment Variables:**
```bash
# IPC Configuration
export CHAMPI_ASSISTANT_MEMORY_PREFIX="champi_assistant"  # Shared memory namespace
export CHAMPI_ASSISTANT_UI_ENABLED="true"                 # Enable/disable UI subprocess
export CHAMPI_ASSISTANT_UI_WINDOW_X="50"                  # UI window X position (pixels)
export CHAMPI_ASSISTANT_UI_WINDOW_Y="50"                  # UI window Y position (pixels)

# General Configuration
export CHAMPI_CONFIG_FILE="/path/to/config.yaml"          # Config file path
export CHAMPI_STT_PROVIDER="whisperlive"                  # STT provider
export CHAMPI_WAKEWORD_KEYWORDS="hey_jarvis,alexa"        # Wake words (comma-separated)
export CHAMPI_LOG_LEVEL="INFO"                            # Logging level
```

---

## 🤖 MCP Server

Champi STT exposes its transcription tools over the
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/), letting
LLM hosts such as Claude Desktop call them directly.

### Install

```bash
pip install 'champi-stt[mcp]'
```

### Start

```bash
champi-stt mcp serve
```

Run `champi-stt mcp serve --help` to see all options including SSE transport.

### Claude Desktop configuration

Add a server entry to your `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "champi-stt": {
      "command": "champi-stt-mcp"
    }
  }
}
```

To select a non-default STT provider, pass the `CHAMPI_STT_PROVIDER` environment variable:

```json
{
  "mcpServers": {
    "champi-stt": {
      "command": "champi-stt-mcp",
      "env": {
        "CHAMPI_STT_PROVIDER": "whisperlive"
      }
    }
  }
}
```

After editing the file, restart Claude Desktop for the change to take effect.

For development use from a source checkout, see [docs/mcp-integration.md](docs/mcp-integration.md).

### Available tools

| Tool | Description |
|---|---|
| `list_providers` | Return the names of all registered STT providers |
| `get_provider_status` | Return health and model information for a named provider |
| `transcribe_audio` | Transcribe a local audio file and return the transcript text |
| `detect_language` | Detect the spoken language in a local audio file |

---

## 📖 Documentation

### Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

### Implementation
See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for complete implementation details.

### Changelog
See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

---

## 🛠️ Development

### Setup Development Environment

Clone repository:
```bash
git clone https://github.com/divagnz/champi-stt.git
```

Navigate to directory:
```bash
cd champi-stt
```

Install with development dependencies:
```bash
uv sync --extra dev --extra all
```

Install pre-commit hooks:
```bash
uv run pre-commit install
```

### Running Tests

Run all tests:
```bash
uv run pytest
```

Run with coverage:
```bash
uv run pytest --cov=src/champi_stt --cov-report=term --cov-report=html
```

Run specific test file:
```bash
uv run pytest tests/test_provider.py
```

### Code Quality

Format code:
```bash
uv run ruff format src/
```

Lint code:
```bash
uv run ruff check src/
```

Type checking:
```bash
uv run mypy src/
```

Run all pre-commit hooks:
```bash
uv run pre-commit run --all-files
```

---

## 🏗️ Project Structure

```
champi-stt/
├── src/champi_stt/
│   ├── core/                  # Generic abstractions
│   │   ├── base_config.py
│   │   ├── base_provider.py
│   │   ├── audio.py
│   │   └── ...
│   ├── providers/             # STT implementations
│   │   └── whisperlive/
│   ├── assistant/             # Voice assistant
│   │   ├── wakeword/          # Wake word engines
│   │   ├── commands/          # Command registry
│   │   ├── service/           # Daemon service
│   │   ├── ipc/               # IPC infrastructure
│   │   │   ├── structs.py    # Binary signal definitions
│   │   │   ├── shared_memory.py
│   │   │   ├── signal_processor.py
│   │   │   ├── signal_reader.py
│   │   │   └── signal_manager.py
│   │   └── ui/                # Visual indicators
│   │       └── wake_indicator_ui.py
│   └── cli.py                 # CLI interface
├── tests/                     # Test suite
├── .github/workflows/         # CI/CD workflows
└── pyproject.toml             # Project configuration
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes using [Conventional Commits](https://www.conventionalcommits.org/)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Commit Message Format

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automatic versioning:

```
feat: add new feature
fix: bug fix
docs: documentation changes
chore: maintenance tasks
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - High-performance Whisper transcription
- [champi-signals](https://github.com/divagnz/champi-signals) - Event-driven signal management
- [imgui-bundle](https://github.com/pthom/imgui_bundle) - ImGui bindings for Python
- [blinker](https://github.com/pallets-eco/blinker) - Fast Python signals/events
- [WebRTC VAD](https://github.com/wiseman/py-webrtcvad) - Voice activity detection
- [Click](https://click.pallets.com/) - CLI framework
- [PyYAML](https://pyyaml.org/) - YAML configuration
- [Resemblyzer](https://github.com/resemble-ai/Resemblyzer) - Speaker identification

---

## 📧 Contact

For questions, issues, or feature requests, please [open an issue](https://github.com/divagnz/champi-stt/issues).

---

**Status**: ✅ **PRODUCTION READY**
