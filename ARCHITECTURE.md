# Champi STT Architecture

## Overview

Champi STT is a modular, multi-provider speech-to-text library designed to support multiple STT backends with a unified interface.

## Directory Structure

```
src/champi_stt/
├── core/                          # Generic abstractions (provider-agnostic)
│   ├── base_config.py            # Abstract configuration base class
│   ├── base_provider.py          # Abstract STT provider interface
│   ├── base_transcriber.py       # Abstract transcriber interface
│   ├── base_model_manager.py     # Abstract model manager interface
│   ├── audio.py                  # Generic audio handling (recording, playback, VAD)
│   ├── preprocessing.py          # Audio preprocessing (normalization, resampling)
│   └── response.py               # Response formatting utilities
│
├── providers/                     # Provider implementations
│   └── whisperlive/              # WhisperLive (faster-whisper) provider
│       ├── config.py             # WhisperLive configuration
│       ├── provider.py           # WhisperLive STT provider
│       ├── transcriber.py        # WhisperLive transcriber
│       ├── models.py             # Model management
│       ├── enums.py              # WhisperLive-specific enums
│       ├── events.py             # Event system
│       └── exceptions.py         # WhisperLive exceptions
│
├── assistant/                     # Voice assistant features
│   ├── wakeword/                 # Wake word detection engines
│   ├── commands/                 # Command registry and execution
│   ├── service/                  # System service/daemon
│   ├── ipc/                      # IPC infrastructure
│   │   ├── structs.py           # Binary signal definitions
│   │   ├── shared_memory.py     # Shared memory manager
│   │   ├── signal_processor.py  # Signal processor (blinker→shared memory)
│   │   ├── signal_reader.py     # Signal reader (shared memory→UI)
│   │   ├── signal_queue.py      # Thread-safe FIFO queue
│   │   └── signal_manager.py    # Assistant signal manager
│   └── ui/                       # Visual indicators
│       └── wake_indicator_ui.py  # GLFW/ImGui wake indicator
│
├── common/                        # Shared utilities
│
├── factory.py                     # Provider factory
├── main.py                        # CLI entry point
└── __init__.py                    # Public API
```

## Design Principles

### 1. **Provider-Agnostic Core**

All generic functionality is extracted into `core/`:
- Audio handling (recording, playback, VAD)
- Audio preprocessing (normalization, resampling)
- Response formatting
- Abstract base classes

### 2. **Provider Implementations**

Each provider (WhisperLive, OpenAI, Deepgram, etc.) implements:
- `BaseSTTConfig` - Provider-specific configuration
- `BaseSTTProvider` - Main provider interface
- `BaseTranscriber` - Low-level transcription logic
- `BaseModelManager` - Model loading/management (if applicable)

### 3. **Factory Pattern**

Providers are instantiated via factory functions:

```python
from champi_stt import get_provider

# Get default provider
provider = get_provider()

# Get specific provider
provider = get_provider("whisperlive", model_size="base")
```

### 4. **Voice Assistant Features**

Modular assistant features:
- **Wake Word**: OpenWakeWord (default), Vosk (alternative)
- **Commands**: Registry-based command execution with exact/regex matching
- **Service**: System daemon for continuous listening
- **IPC Infrastructure**: Shared memory communication for UI

### 5. **IPC Infrastructure for Wake Indicator**

The assistant uses a sophisticated IPC (Inter-Process Communication) system for real-time UI updates:

#### Signal Flow Architecture
```
Daemon Process                           UI Subprocess
├─ Blinker Signals                      ├─ SignalReader
│  ├─ state                              │  └─ poll_once()
│  ├─ processing                         │
│  └─ error                              ├─ GLFW Window
│                                        │  └─ Render visual states
├─ SignalProcessor                       │
│  ├─ Connect signals                    └─ ACK tracking
│  ├─ FIFO Queue (100 items)
│  └─ Pack to binary struct
│
├─ SharedMemoryManager
│  ├─ Memory lanes (per signal type):
│  │  ├─ champi_assistant_state_change
│  │  ├─ champi_assistant_wake_detected
│  │  ├─ champi_assistant_recording
│  │  ├─ champi_assistant_transcribing
│  │  ├─ champi_assistant_executing
│  │  └─ champi_assistant_error
│  └─ ACK regions (for signal loss detection)
```

#### Components

1. **Signal Types (AssistantSignalType)**
   - `STATE_CHANGE = 1` - Assistant state updates
   - `WAKE_DETECTED = 2` - Wake word detection
   - `RECORDING = 3` - Audio recording status
   - `TRANSCRIBING = 4` - Transcription progress
   - `EXECUTING = 5` - Command execution
   - `ERROR = 6` - Error events

2. **Binary Struct Serialization**
   - Fixed-size structs for cross-process safety
   - Sequence number tracking
   - Padding for consistent sizes
   - Example: `STATE_CHANGE_STRUCT = struct.Struct(f"=QB{MAX_STATE_SIZE}s")`

3. **Memory Lane System**
   - Each signal type gets dedicated memory region
   - Data region: Contains packed signal struct
   - ACK region: Tracks reader acknowledgment
   - Configurable prefix for namespace isolation

4. **Signal Processor**
   - Bridges blinker signals to shared memory
   - Thread-safe FIFO queue (100 max items)
   - Data mappers for signal transformation
   - ACK-based signal loss detection

5. **UI Subprocess**
   - GLFW-based OpenGL rendering
   - 60 Hz polling rate
   - Visual state indicators
   - Standalone executable for testing

#### Configuration

Environment variables:
- `CHAMPI_ASSISTANT_MEMORY_PREFIX` - Memory namespace (default: "champi_assistant")
- `CHAMPI_ASSISTANT_UI_ENABLED` - Enable/disable UI (default: "true")

Config fields:
- `ipc_memory_prefix` - Shared memory prefix
- `ipc_ui_window_x` - UI window X position
- `ipc_ui_window_y` - UI window Y position
- `ipc_ui_poll_rate_hz` - Signal polling rate

## Usage Examples

### Basic Transcription

```python
from champi_stt import get_provider

provider = get_provider()
await provider.initialize()

result = await provider.transcribe("audio.wav")
print(result["text"])
```

### Custom Configuration

```python
from champi_stt import get_provider
from champi_stt.providers.whisperlive import WhisperLiveConfig

config = WhisperLiveConfig(
    model_size="base",
    device="cpu",
    language="en"
)

provider = get_provider("whisperlive", config=config)
await provider.initialize()
```

### Recording with VAD

```python
from champi_stt.core.audio import record_audio_with_vad

# Record until silence detected
audio = await record_audio_with_vad(
    max_duration=10.0,
    silence_threshold_ms=800
)
```

## Adding New Providers

To add a new provider (e.g., OpenAI):

1. Create `providers/openai/` directory
2. Implement:
   - `OpenAIConfig(BaseSTTConfig)`
   - `OpenAISTTProvider(BaseSTTProvider)`
   - `OpenAITranscriber(BaseTranscriber)` (if needed)
3. Add to `factory.py`
4. Update `list_providers()`

## Backwards Compatibility

The library maintains backwards compatibility by exposing WhisperLive classes directly:

```python
# Old way (still works)
from champi_stt import WhisperLiveConfig, WhisperLiveSTTProvider

# New way (recommended)
from champi_stt import get_provider
```

## Future Extensions

### Phase 2: Wake Word Detection
- Porcupine integration
- Vosk small model support
- Audio streaming for continuous detection

### Phase 3: Command System
- Command registry
- Intent parsing
- Action execution (shell, API, Python)

### Phase 4: System Service
- systemd integration (Linux)
- launchd integration (macOS)
- Windows Service support
- Continuous listening daemon
