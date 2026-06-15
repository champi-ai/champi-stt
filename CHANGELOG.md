# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


### Added
- Multi-provider STT architecture with abstract base classes
- WhisperLive provider implementation (local, faster-whisper backend)
- Wake word detection system (OpenWakeWord default, Vosk alternative)
- Voice command system with exact and regex pattern matching
- Command executor supporting shell, HTTP API, and Python function execution
- Voice assistant service/daemon with continuous listening mode
- **IPC-based Wake Indicator UI**:
  - Real-time visual status indicator using GLFW/ImGui
  - Subprocess-based UI with shared memory IPC
  - 6 signal types: STATE_CHANGE, WAKE_DETECTED, RECORDING, TRANSCRIBING, EXECUTING, ERROR
  - Binary struct-based communication for low latency
  - Visual states: IDLE (gray), AWAKE (green pulse), RECORDING (red), TRANSCRIBING (blue), EXECUTING (yellow), ERROR (red flash)
  - AssistantSignalManager using champi-signals for event-driven architecture
  - AssistantSharedMemoryManager with dedicated memory lanes per signal type
  - AssistantSignalProcessor bridging blinker signals to shared memory via FIFO queue
  - AssistantSignalReader for consuming signals from shared memory
  - ACK tracking for signal loss detection
  - Configurable memory prefix for namespace isolation (compatible with mcp_champi)
  - Environment variable configuration (CHAMPI_ASSISTANT_MEMORY_PREFIX, CHAMPI_ASSISTANT_UI_ENABLED)
  - UI subprocess logging to file for debugging
- Speaker identification using Resemblyzer voice embeddings
- Comprehensive CLI with multiple subcommands
- YAML-based configuration system
- Example configuration files for assistant and commands
- Built-in voice commands (15+ commands)
- Generic audio handling (recording, playback, VAD)
- Audio preprocessing utilities (normalization, resampling)
- Response formatting utilities
- Factory pattern for provider instantiation
- Event-driven architecture using champi-signals and blinker
- MIT License file
- Complete development tooling setup:
  - Pre-commit hooks with security scanning (detect-secrets, bandit)
  - Conventional commits for semantic versioning
  - Code quality tools (black, ruff, mypy)
  - Comprehensive linting configuration in pyproject.toml
- GitHub Actions CI/CD workflows:
  - CI pipeline (lint, security, test, build) with matrix testing
  - Pre-commit CI workflow
  - Automated release workflow with PyPI publishing
- All dependencies from champi project (50+ packages)
- UV package manager configuration with PyTorch CUDA support
- Tool scripts for security, linting, formatting, and testing
- Project URLs (Homepage, Repository, Issues)

### Documentation
- README.md with badges, quick start guide, and development instructions
- ARCHITECTURE.md with detailed architecture documentation
- IMPLEMENTATION_SUMMARY.md with complete project overview
- CHANGELOG.md for version history tracking
- SETUP_COMPLETE.md with setup instructions and next steps
- DEPENDENCIES_VALIDATION.md with complete validation report
- Example configuration files with detailed comments
- .secrets.baseline for secrets detection

### Changed
- Updated author information to Divagnz
- Updated all repository URLs to divagnz/champi-stt
- Synchronized all dependencies with main champi project
- Updated Ruff configuration to match champi (line-length: 88)
- Updated Black configuration to match champi standards
- Replaced Porcupine with OpenWakeWord as default wake word engine
- UI subprocess logging now redirects to file instead of DEVNULL for debugging

### Deprecated
- `wake_indicator_position` config field - UI position now configured via `ipc_ui_window_x` and `ipc_ui_window_y`

## v1.2.0 (2026-06-15)

### Feat

- **mcp**: add microphone recording tools — listen_once, listen_until_silence, list_audio_devices

## v1.1.2 (2026-06-14)

### Fix

- **mcp**: add [mcp] extra to uvx command and uvx Claude Desktop config (#95)

## v1.1.1 (2026-06-14)

### Fix

- **deps**: embed champi-signals wheel URL directly in package metadata (#93)

## v1.1.0 (2026-06-13)

### Feat

- **release**: add release_url config auto-updated on version bump (#92)

## v1.0.2 (2026-06-13)

### Fix

- **deps**: update vulnerable transitive dependencies (pillow, requests, urllib3, setuptools, idna) (#91)

## v1.0.1 (2026-06-13)

### Fix

- **lint**: ruff check and format clean across all files (#89)

## v1.0.0 (2026-06-12)

### Feat

- **ci**: add v* tag-triggered GitHub Release workflow
- **tests**: add MCP server stdio handshake integration test (#72)
- **mcp**: lazy provider lifecycle via FastMCP lifespan, env var, SSE transport (#68)
- add API reference docs via mkdocstrings (#47)
- define and document public API surface for v1.0 stability guarantee (#46)
- add benchmark suite for transcription latency and memory (#45)
- add REST API server for mobile and external integration (#44)
- add multi-room audio manager for multiple simultaneous input devices (#43)
- add speaker diarization via pyannote.audio (#42)
- add real-time streaming transcription pipeline (#41)
- add MkDocs documentation site with GitHub Pages deployment (#40)
- add FeedbackTheme enum and volume control to audio feedback (#39)
- add web configuration UI server and serve-config CLI command (#38)
- add AssemblyAI STT provider with real-time streaming
- add launchd plist installer for macOS and extend service CLI
- add systemd user service installer and CLI subcommands
- implement Vosk wake word engine
- enable mypy strict mode on core and assistant/commands modules
- alpha release — IPC, ImGui 3D sphere, audio analysis, tests
- add core library structure and initial implementation

### Fix

- **ci**: remove paths-ignore from release workflow tag trigger
- resolve bandit High/Medium security findings pre-release (#48)
- stabilize test suite and add missing response/provider APIs
- stabilize IPC — handler lock, cleanup rollback, stop timeout, docs

### Refactor

- canonicalize energy sphere renderer, mark imgui variant as experimental
- move heavy deps to optional extras, remove build tools from runtime deps
