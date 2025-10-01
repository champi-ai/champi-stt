# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Multi-provider STT architecture with abstract base classes
- WhisperLive provider implementation (local, faster-whisper backend)
- Wake word detection system (Porcupine integration)
- Voice command system with exact and regex pattern matching
- Command executor supporting shell, HTTP API, and Python function execution
- Voice assistant service/daemon with continuous listening mode
- Comprehensive CLI with multiple subcommands
- YAML-based configuration system
- Example configuration files for assistant and commands
- Built-in voice commands (15+ commands)
- Generic audio handling (recording, playback, VAD)
- Audio preprocessing utilities (normalization, resampling)
- Response formatting utilities
- Factory pattern for provider instantiation
- Event-driven architecture using champi-signals
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

## [0.1.0] - 2025-10-01

### Added
- Initial release
- Multi-provider architecture foundation
- WhisperLive provider
- Voice assistant features
- CLI interface
- Documentation
