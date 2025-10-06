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
- **Porcupine** by Picovoice (recommended)
- **Vosk** with small models
- Customizable sensitivity and keywords
- Low-latency detection

### 🎯 **Voice Command System**
- Exact phrase matching
- Regex pattern matching
- Multiple action types:
  - Shell commands
  - HTTP API calls
  - Python function execution
- YAML configuration
- Built-in commands (time, web search, volume control, etc.)

### 🤖 **Voice Assistant Service**
- Continuous listening mode
- System service/daemon support
- Automatic silence detection (VAD)
- Event-driven architecture

---

## 📦 Installation

### Basic Installation (WhisperLive only)

```bash
pip install champi-stt
```

### With Wake Word Support

```bash
# Porcupine (recommended)
pip install champi-stt[porcupine]

# Vosk
pip install champi-stt[vosk]

# All wake word engines
pip install champi-stt[all]
```

### Development Installation

```bash
git clone https://github.com/divagnz/champi-stt.git
cd champi-stt
pip install -e ".[dev,all]"
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

```bash
# Transcribe audio file
champi-stt transcribe audio.wav

# With custom provider and format
champi-stt transcribe audio.wav --provider whisperlive --format json
```

### 3. Voice Assistant

```bash
# Create configuration
champi-stt assistant init-config --output config.yaml

# Edit config.yaml with your settings
# - Add your Porcupine access_key from https://console.picovoice.ai
# - Choose wake words
# - Configure STT provider

# Start voice assistant
champi-stt assistant start --config config.yaml
```

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

```bash
# Clone repository
git clone https://github.com/divagnz/champi-stt.git
cd champi-stt

# Install with development dependencies
pip install -e ".[dev,all]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/champi_stt --cov-report=term --cov-report=html

# Run specific test file
pytest tests/test_provider.py
```

### Code Quality

```bash
# Format code
black src/

# Lint code
ruff check src/

# Type checking
mypy src/

# Run all pre-commit hooks
pre-commit run --all-files
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
│   │   ├── wakeword/
│   │   ├── commands/
│   │   └── service/
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
- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
- [Porcupine](https://picovoice.ai/platform/porcupine/) by Picovoice
- [WebRTC VAD](https://github.com/wiseman/py-webrtcvad)
- [Click](https://click.pallets.com/)
- [PyYAML](https://pyyaml.org/)

---

## 📧 Contact

For questions, issues, or feature requests, please [open an issue](https://github.com/divagnz/champi-stt/issues).

---

**Status**: ✅ **PRODUCTION READY**
