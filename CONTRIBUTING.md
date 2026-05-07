# Contributing to Champi STT

Thank you for your interest in contributing to Champi STT! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:

Clone your fork:
```bash
git clone https://github.com/YOUR_USERNAME/champi-stt.git
```

Navigate to directory:
```bash
cd champi-stt
```

3. **Add upstream remote**:

```bash
git remote add upstream https://github.com/divagnz/champi-stt.git
```

## Development Setup

### Prerequisites

- Python 3.12+
- [UV package manager](https://github.com/astral-sh/uv)
- Git

### Initial Setup

Install UV if not already installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create virtual environment:
```bash
uv venv
```

Activate virtual environment:
```bash
source .venv/bin/activate
```

Note: On Windows use:
```bash
.venv\Scripts\activate
```

Install dependencies:
```bash
uv pip install -e ".[dev,test]"
```

Install pre-commit hooks:
```bash
pre-commit install
```

### Install Additional Dependencies

For wake word detection:
```bash
uv pip install openwakeword
```

For speaker identification:
```bash
uv pip install resemblyzer
```

For GPU support (optional):
```bash
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu129
```

## Making Changes

### Branch Naming Convention

- `feat/feature-name` - For new features
- `fix/bug-description` - For bug fixes
- `docs/documentation-update` - For documentation changes
- `refactor/refactoring-description` - For code refactoring
- `test/test-description` - For test additions/modifications

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(ipc): add cleanup command for orphaned memory regions

Implements CLI command to clean up shared memory regions left
by crashed processes.

Closes #123
```

```
fix(config): correct IPC config loading from YAML

IPC settings were being read from service_config instead of
ipc_config, causing settings to be ignored.
```

## Code Style

### Python Style Guide

We use **Ruff** for linting and **Black** for formatting:

Format code:
```bash
uv run ruff format src/champi_stt/
```

Lint code:
```bash
uv run ruff check src/champi_stt/
```

Auto-fix lint issues:
```bash
uv run ruff check --fix src/champi_stt/
```

### Code Standards

1. **Type Hints**: All functions must have type annotations
   ```python
   def process_audio(audio: np.ndarray, sample_rate: int) -> dict[str, Any]:
       """Process audio data."""
       pass
   ```

2. **Docstrings**: All public functions/classes must have docstrings
   ```python
   def cleanup_orphaned_regions(name_prefix: str = "champi_assistant") -> List[str]:
       """Clean up orphaned shared memory regions.

       This utility function removes shared memory regions that were left behind
       by crashed processes or improper shutdowns.

       Args:
           name_prefix: Memory region prefix to clean up

       Returns:
           List of cleaned region names
       """
   ```

3. **Line Length**: Maximum 88 characters (Black default)

4. **Imports**: Organized by:
   - Standard library
   - Third-party packages
   - Local imports

   ```python
   import os
   from typing import List, Optional

   import numpy as np
   from loguru import logger

   from champi_stt.core.audio import record_audio
   ```

## Testing

### Running Tests

Run all tests:
```bash
uv run pytest
```

Run with coverage:
```bash
uv run pytest --cov=src/champi_stt --cov-report=html
```

Run specific test file:
```bash
uv run pytest tests/test_ipc_shared_memory.py
```

Run specific test:
```bash
uv run pytest tests/test_ipc_shared_memory.py::TestSharedMemoryManager::test_create_regions
```

### Writing Tests

1. **Test file naming**: `test_<module_name>.py`
2. **Test function naming**: `test_<what_is_being_tested>`
3. **Use fixtures** for common setup:
   ```python
   @pytest.fixture
   def sample_audio():
       return np.random.randint(-32768, 32767, 16000, dtype=np.int16)
   ```

4. **Test coverage**: Aim for >80% coverage on new code

### Test Categories

- **Unit tests**: `tests/test_*.py`
- **Integration tests**: `tests/test_*_integration.py`
- **Mark slow tests**: `@pytest.mark.slow`
- **Mark integration tests**: `@pytest.mark.integration`

## Pull Request Process

### Before Submitting

1. **Update your fork**:

Fetch upstream:
```bash
git fetch upstream
```

Rebase on main:
```bash
git rebase upstream/main
```

2. **Run pre-commit checks**:

```bash
pre-commit run --all-files
```

3. **Run tests**:

```bash
uv run pytest
```

4. **Update documentation** if needed

### Submitting PR

1. **Push to your fork**:

```bash
git push origin feat/your-feature
```

2. **Create Pull Request** on GitHub

3. **Fill out PR template** with:
   - Description of changes
   - Related issues (if any)
   - Testing done
   - Screenshots (for UI changes)

### PR Review Process

- At least one maintainer approval required
- All CI checks must pass
- No merge conflicts
- Code review feedback addressed

### After PR is Merged

1. **Delete your branch**:

Delete local branch:
```bash
git branch -d feat/your-feature
```

Delete remote branch:
```bash
git push origin --delete feat/your-feature
```

2. **Update your fork**:

Checkout main:
```bash
git checkout main
```

Pull latest changes:
```bash
git pull upstream main
```

## Reporting Bugs

### Before Reporting

1. **Search existing issues** to avoid duplicates
2. **Test with latest version**
3. **Check documentation** for known issues

### Bug Report Template

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Run command '...'
2. See error

**Expected behavior**
What you expected to happen.

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.12]
- Champi STT version: [e.g., 0.1.0]

**Additional context**
Logs, screenshots, etc.
```

## Feature Requests

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions you've thought about.

**Additional context**
Any other context or screenshots.
```

## Development Tips

### Running Assistant Locally

Create config:
```bash
champi-stt assistant init-config
```

Start assistant:
```bash
champi-stt assistant start --config assistant_config.yaml
```

### Debugging IPC

Check shared memory status:
```bash
champi-stt ipc status
```

Clean up orphaned regions:
```bash
champi-stt ipc cleanup
```

Test UI standalone:
```bash
champi-stt ipc test-ui
```

### Performance Profiling

```python
import cProfile
import pstats

with cProfile.Profile() as pr:
    # Your code here
    pass

stats = pstats.Stats(pr)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

## Questions?

- **Documentation**: [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md)
- **IPC Guide**: [docs/IPC.md](docs/IPC.md)
- **Issues**: [GitHub Issues](https://github.com/divagnz/champi-stt/issues)
- **Discussions**: [GitHub Discussions](https://github.com/divagnz/champi-stt/discussions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
