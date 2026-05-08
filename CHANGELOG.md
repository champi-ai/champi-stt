# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-05-07

### Added
- `TranscriptionResponse` and `TranscriptionSegment` dataclasses in `core/response.py` — standardized return type for all STT providers
- `STTResponse` alias in `core/response.py` for backwards compatibility
- `TranscriptionOptions` dataclass in `whisperlive/models.py` for structured transcription parameters
- `WhisperLiveProvider` alias for `WhisperLiveSTTProvider`
- `is_initialized` property, `name` attribute, `_get_model_path()`, and async context manager support on `WhisperLiveSTTProvider`
- `__aenter__` / `__aexit__` on `WhisperLiveSTTProvider` for `async with` usage
- Thread safety for `AssistantSignalReader` handler dict via `threading.Lock`
- Rollback on partial `SharedMemoryManager.create_regions()` failure
- `stop()` calls `disconnect_all()` before thread join in `AssistantSignalProcessor`
- Thread safety and platform notes documented in `docs/IPC.md`
- ImGui energy sphere renderer canonicalized: `energy_sphere_renderer.py` is the single import surface backed by the enhanced implementation

### Fixed
- `sounddevice` import is now guarded with try/except OSError in `core/audio.py`, `provider.py`, and `transcriber.py` — prevents crash when PortAudio library is missing
- `torch` import is now guarded with try/except ImportError in `whisperlive/models.py` — prevents crash when PyTorch is not installed
- `WhisperLiveConfig` defaults changed to sensible values: `model_size="base"`, `device="auto"`, `language=None`
- Enum instances passed as `model_size` or `compute_type` to `WhisperLiveConfig` are now normalized to string values
- `transcribe()` now handles `pathlib.Path` objects as audio input
- `.python-version` file restored (was incorrectly deleted and added to `.gitignore`)
- Pre-commit hooks: fixed `__all__` sorting, bare `except:` clauses, unused variables, and `N811` import naming violations

### Changed
- `WhisperLiveSTTProvider.transcribe()` return type changed from `str | dict` to `TranscriptionResponse`
- Removed `simpleaudio` from core dependencies (fails to build on Linux with Python 3.12)
- Moved heavy optional dependencies to extras: `torch`, `imgui-bundle`, `spacy`, `openwakeword`, `resemblyzer`
- Added `pytest-mock` to dev dependencies
- Test suite: `test_whisperlive_provider.py` updated to match current implementation APIs

### Deprecated
- The `response_format` parameter on `WhisperLiveSTTProvider.transcribe()` is kept for API compatibility but no longer affects the return type (always returns `TranscriptionResponse`)

## [0.0.1] - 2025-10-21

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
