# IPC Infrastructure Guide

## Overview

The **champi-stt** assistant uses a sophisticated Inter-Process Communication (IPC) system to provide real-time UI updates via a shared memory architecture. This enables a low-latency, event-driven communication channel between the daemon process and the UI subprocess.

### Key Benefits

- **Low Latency**: Binary struct-based serialization for minimal overhead
- **Decoupled Architecture**: UI subprocess runs independently
- **Signal Loss Detection**: ACK tracking ensures no signals are missed
- **Namespace Isolation**: Configurable memory prefix prevents conflicts
- **Event-Driven**: Blinker signals bridge to shared memory seamlessly

---

## Architecture

### Signal Flow Diagram

```
┌─────────────────────────────────────┐         ┌──────────────────────────────────┐
│        Daemon Process               │         │        UI Subprocess             │
│                                     │         │                                  │
│  ┌──────────────────────────────┐  │         │  ┌───────────────────────────┐   │
│  │   Blinker Signals            │  │         │  │   AssistantSignalReader   │   │
│  │   • state (STATE_CHANGE)     │  │         │  │   • poll_once()           │   │
│  │   • processing (WAKE, etc.)  │  │         │  │   • register_handler()    │   │
│  │   • error (ERROR)            │  │         │  │   • read from memory      │   │
│  └──────────────────────────────┘  │         │  └───────────────────────────┘   │
│              ↓                      │         │              ↑                    │
│  ┌──────────────────────────────┐  │         │              │                    │
│  │   AssistantSignalProcessor   │  │         │              │                    │
│  │   • connect_signal()         │  │         │              │                    │
│  │   • data_mapper functions    │  │         │              │                    │
│  │   • FIFO Queue (100 items)   │  │         │              │                    │
│  │   • Pack to binary struct    │  │         │              │                    │
│  └──────────────────────────────┘  │         │              │                    │
│              ↓                      │         │              │                    │
│  ┌──────────────────────────────┐  │         │              │                    │
│  │  AssistantSharedMemoryMgr    │  │         │              │                    │
│  │   Memory Lanes (per type):   │  │ SHARED  │              │                    │
│  │   • champi_assistant_state   │◄─┼─────────┼──────────────┤                    │
│  │   • champi_assistant_wake    │  │ MEMORY  │              │                    │
│  │   • champi_assistant_rec     │  │         │              │                    │
│  │   • champi_assistant_trans   │  │         │              │                    │
│  │   • champi_assistant_exec    │  │         │              │                    │
│  │   • champi_assistant_error   │  │         │              │                    │
│  │                              │  │         │              │                    │
│  │   ACK Regions (per type):    │  │         │              │                    │
│  │   • *_ack (sequence nums)    │◄─┼─────────┼──────────────┤                    │
│  └──────────────────────────────┘  │         │              │                    │
│                                     │         │              │                    │
│  ┌──────────────────────────────┐  │         │  ┌───────────────────────────┐   │
│  │   AssistantSignalManager     │  │         │  │   GLFW Window + ImGui     │   │
│  │   (Singleton via champi-sig) │  │         │  │   • Render visual states  │   │
│  │   • state.send()             │  │         │  │   • 60 Hz polling         │   │
│  │   • processing.send()        │  │         │  │   • ACK tracking          │   │
│  │   • error.send()             │  │         │  └───────────────────────────┘   │
│  └──────────────────────────────┘  │         │                                  │
└─────────────────────────────────────┘         └──────────────────────────────────┘
```

---

## Signal Types

### AssistantSignalType Enum

All signals are typed using the `AssistantSignalType` enum:

```python
class AssistantSignalType(IntEnum):
    """Signal types for assistant IPC."""
    STATE_CHANGE = 1    # General state transitions
    WAKE_DETECTED = 2   # Wake word detected
    RECORDING = 3       # Audio recording status
    TRANSCRIBING = 4    # Transcription progress
    EXECUTING = 5       # Command execution
    ERROR = 6           # Error events
```

### Binary Struct Definitions

Each signal type has a fixed-size binary struct for cross-process communication:

```python
# Maximum sizes for variable-length fields
MAX_STATE_SIZE = 64      # State string
MAX_WAKE_WORD_SIZE = 64  # Wake word string
MAX_TEXT_SIZE = 256      # Partial transcription text
MAX_COMMAND_SIZE = 256   # Command text
MAX_ERROR_SIZE = 512     # Error message

# Struct definitions (using struct.Struct for performance)
STATE_CHANGE_STRUCT = struct.Struct(f"=QB{MAX_STATE_SIZE}s")
WAKE_DETECTED_STRUCT = struct.Struct(f"=QB{MAX_WAKE_WORD_SIZE}s")
RECORDING_STRUCT = struct.Struct("=QdB")
TRANSCRIBING_STRUCT = struct.Struct(f"=QB{MAX_TEXT_SIZE}sB")
EXECUTING_STRUCT = struct.Struct(f"=QB{MAX_COMMAND_SIZE}s")
ERROR_STRUCT = struct.Struct(f"=QB{MAX_ERROR_SIZE}sB{64}s")

# ACK struct (sequence number only)
ACK_STRUCT = struct.Struct("=Q")
```

**Field Breakdown:**
- `Q` - Sequence number (unsigned long long, 8 bytes)
- `d` - Double (recording duration, 8 bytes)
- `B` - Boolean/byte (is_active, is_final, error_type, 1 byte)
- `{N}s` - Fixed-size string (padded with null bytes)

---

## Memory Lane System

### Memory Region Naming

Each signal type gets **two** shared memory regions:

1. **Data Region**: `{prefix}_{signal_type.lower()}`
   - Example: `champi_assistant_wake_detected`
   - Stores packed binary struct

2. **ACK Region**: `{prefix}_{signal_type.lower()}_ack`
   - Example: `champi_assistant_wake_detected_ack`
   - Stores last acknowledged sequence number

### Region Lifecycle

**Creator (Daemon)**:
```python
memory_mgr = AssistantSharedMemoryManager(name_prefix="champi_assistant")
memory_mgr.create_regions()  # Creates all regions with zero initialization
memory_mgr.write_signal(AssistantSignalType.WAKE_DETECTED, packed_data)
memory_mgr.cleanup()  # Unlinks regions on shutdown
```

**Consumer (UI Subprocess)**:
```python
memory_mgr = AssistantSharedMemoryManager(name_prefix="champi_assistant")
memory_mgr.attach_regions()  # Attaches to existing regions
data = memory_mgr.read_signal(AssistantSignalType.WAKE_DETECTED)
memory_mgr.cleanup()  # Closes but does NOT unlink
```

---

## Component Deep Dive

### 1. AssistantSignalManager

**Location**: `champi_stt/assistant/ipc/signal_manager.py`

Inherits from `champi_signals.BaseSignalManager` (singleton pattern).

```python
from champi_stt.assistant.ipc import AssistantSignalManager

# Get singleton instance
signal_mgr = AssistantSignalManager()

# Emit signals
signal_mgr.state.send(
    event_type="state",
    sub_event="LISTENING_START",
    data={"state": "listening"}
)

signal_mgr.processing.send(
    event_type="processing",
    sub_event="WAKE_DETECTED",
    data={"wake_word": "hey_jarvis"}
)

signal_mgr.error.send(
    event_type="error",
    sub_event="TRANSCRIPTION_ERROR",
    data={"error_message": "Timeout", "error_type": "timeout"}
)
```

**Available Signals:**
- `state` - General state changes
- `processing` - Processing events (wake, recording, transcribing, executing)
- `error` - Error events

### 2. AssistantSignalProcessor

**Location**: `champi_stt/assistant/ipc/signal_processor.py`

Bridges blinker signals to shared memory via FIFO queue.

```python
from champi_stt.assistant.ipc import AssistantSignalProcessor

processor = AssistantSignalProcessor(memory_manager, max_queue_size=100)

# Connect signal with data mapper
processor.connect_signal(
    signal_mgr.processing,
    AssistantSignalType.WAKE_DETECTED,
    data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")}
)

# Start processing (processes queue in background)
processor.start()

# Cleanup
processor.stop()
```

**Data Mappers**: Transform signal kwargs to struct-compatible dict:

```python
# Example: STATE_CHANGE mapper
data_mapper=lambda **kw: {
    "state": kw.get("sub_event", "").replace("_START", "").replace("_FINISH", "").lower()
}

# Example: RECORDING mapper
data_mapper=lambda **kw: {
    "duration": kw.get("duration", 0.0),
    "is_active": kw.get("is_active", False)
} if "RECORDING" in kw.get("sub_event", "") else None
```

**Queue Behavior:**
- Max 100 items (configurable)
- Drops oldest if full (logs warning)
- Thread-safe with `queue.Queue`

### 3. AssistantSharedMemoryManager

**Location**: `champi_stt/assistant/ipc/shared_memory.py`

Manages memory regions and ACK tracking.

```python
from champi_stt.assistant.ipc import AssistantSharedMemoryManager

# Creator workflow
mgr = AssistantSharedMemoryManager(name_prefix="champi_assistant")
mgr.create_regions()
mgr.write_signal(AssistantSignalType.STATE_CHANGE, packed_data)
mgr.write_ack(AssistantSignalType.STATE_CHANGE, seq_num=42)
mgr.cleanup()  # Unlinks

# Consumer workflow
mgr = AssistantSharedMemoryManager(name_prefix="champi_assistant")
mgr.attach_regions()
data = mgr.read_signal(AssistantSignalType.STATE_CHANGE)
ack_seq = mgr.read_ack(AssistantSignalType.STATE_CHANGE)
mgr.cleanup()  # Closes only
```

**Context Manager Support:**
```python
with AssistantSharedMemoryManager() as mgr:
    mgr.create_regions()
    # ... use regions ...
# Auto-cleanup on exit
```

### 4. AssistantSignalReader

**Location**: `champi_stt/assistant/ipc/signal_reader.py`

Reads signals from shared memory in UI subprocess.

```python
from champi_stt.assistant.ipc.signal_reader import AssistantSignalReader

reader = AssistantSignalReader(memory_manager)

# Register handlers
def on_wake_detected(signal_data):
    print(f"Wake word: {signal_data.data['wake_word']}")

reader.register_handler(AssistantSignalType.WAKE_DETECTED, on_wake_detected)

# Poll once per frame (60 Hz typically)
while running:
    reader.poll_once()
    # ... render UI ...
    time.sleep(1/60)

reader.stop()
```

**Signal Loss Detection:**
- Compares last read sequence number with current
- Logs warning if gap detected
- Continues processing (no signal dropped)

---

## Usage Examples

### Example 1: Adding a New Signal Type

**Step 1**: Add to enum
```python
# champi_stt/assistant/ipc/structs.py
class AssistantSignalType(IntEnum):
    # ... existing ...
    AUDIO_LEVEL = 7  # New signal type
```

**Step 2**: Define struct
```python
# structs.py
AUDIO_LEVEL_STRUCT = struct.Struct("=Qd")  # seq_num, level (0.0-1.0)

def get_struct_size(signal_type: AssistantSignalType) -> int:
    structs = {
        # ... existing ...
        AssistantSignalType.AUDIO_LEVEL: AUDIO_LEVEL_STRUCT.size,
    }
    return structs[signal_type]
```

**Step 3**: Add pack/unpack functions
```python
def pack_audio_level(seq_num: int, level: float) -> bytes:
    return AUDIO_LEVEL_STRUCT.pack(seq_num, level)

def unpack_audio_level(data: bytes) -> dict:
    seq_num, level = AUDIO_LEVEL_STRUCT.unpack(data)
    return {"seq_num": seq_num, "level": level}
```

**Step 4**: Connect in daemon
```python
# daemon.py
self._signal_processor.connect_signal(
    self._signal_manager.processing,
    AssistantSignalType.AUDIO_LEVEL,
    data_mapper=lambda **kw: {"level": kw.get("level", 0.0)}
)
```

**Step 5**: Handle in UI
```python
# wake_indicator_ui.py
reader.register_handler(
    AssistantSignalType.AUDIO_LEVEL,
    lambda sig: self.update_audio_meter(sig.data["level"])
)
```

### Example 2: Cleanup Orphaned Regions

```python
from champi_stt.assistant.ipc import cleanup_orphaned_regions

# Clean all champi_assistant_* regions
cleaned = cleanup_orphaned_regions(name_prefix="champi_assistant")
print(f"Cleaned {len(cleaned)} orphaned regions")
```

### Example 3: Custom Memory Prefix

```python
# Daemon with custom prefix
signal_mgr = AssistantSignalManager()
memory_mgr = AssistantSharedMemoryManager(name_prefix="my_custom_prefix")
memory_mgr.create_regions()

processor = AssistantSignalProcessor(memory_mgr)
# ... connect signals ...

# UI subprocess must use same prefix
memory_mgr = AssistantSharedMemoryManager(name_prefix="my_custom_prefix")
memory_mgr.attach_regions()
```

---

## Configuration

### Environment Variables

```bash
# Memory namespace (default: "champi_assistant")
export CHAMPI_ASSISTANT_MEMORY_PREFIX="champi_assistant"

# Enable/disable UI subprocess (default: "true")
export CHAMPI_ASSISTANT_UI_ENABLED="true"

# UI window position (default: 50, 50)
export CHAMPI_ASSISTANT_UI_WINDOW_X="100"
export CHAMPI_ASSISTANT_UI_WINDOW_Y="100"
```

### Config File (assistant_config.yaml)

```yaml
# IPC Configuration
ipc_memory_prefix: "champi_assistant"
ipc_ui_window_x: 50
ipc_ui_window_y: 50
ipc_ui_poll_rate_hz: 60
```

### AssistantConfig Fields

```python
@dataclass
class AssistantConfig:
    # ... other fields ...

    # IPC settings
    ipc_memory_prefix: str = "champi_assistant"
    ipc_ui_window_x: int = 50
    ipc_ui_window_y: int = 50
    ipc_ui_poll_rate_hz: int = 60

    # Deprecated
    wake_indicator_position: Optional[Tuple[int, int]] = None  # Use ipc_ui_window_x/y
```

---

## Debugging and Troubleshooting

### Enable Debug Logging

```python
import logging
logging.getLogger("champi_stt.assistant.ipc").setLevel(logging.DEBUG)
```

### UI Subprocess Logs

UI logs are written to `{cache_dir}/ui.log`:

```bash
# Default location
tail -f ~/.cache/champi_stt/ui.log
```

### Common Issues

**1. "Shared memory region not found"**
- **Cause**: UI subprocess started before daemon creates regions
- **Fix**: Ensure daemon calls `memory_mgr.create_regions()` before spawning UI

**2. "Signal loss detected"**
- **Cause**: Queue overflow (>100 items) or slow consumer
- **Fix**: Increase queue size or reduce signal emission rate

**3. "Orphaned shared memory"**
- **Cause**: Daemon crashed without cleanup
- **Fix**: Run `cleanup_orphaned_regions()` or restart system

**4. UI not updating**
- **Check**: Are signals being emitted? (check daemon logs)
- **Check**: Is `poll_once()` being called in UI loop?
- **Check**: Are handlers registered correctly?

### Manual Memory Inspection

```bash
# List shared memory regions (Linux)
ls -lh /dev/shm/ | grep champi_assistant

# Remove manually (if needed)
rm /dev/shm/champi_assistant_*
```

---

## Performance Considerations

### Latency

- **Struct packing**: ~1-5 μs per signal
- **Memory write**: ~10-50 μs
- **Polling overhead**: ~100-500 μs per poll (60 Hz)
- **Total latency**: <1ms for typical signal

### Memory Usage

- **Per signal type**: ~512-1024 bytes (data + ACK)
- **Total for 6 types**: ~6 KB
- **Queue (100 items)**: ~10-50 KB

### Optimization Tips

1. **Reduce poll rate** if 60 Hz is overkill (e.g., 30 Hz)
2. **Batch signals** if emitting multiple in quick succession
3. **Use data mappers** to filter unnecessary signals
4. **Limit string sizes** in structs (truncate if needed)

---

## Testing Strategies

### Unit Tests

```python
import pytest
from champi_stt.assistant.ipc import AssistantSharedMemoryManager, AssistantSignalType
from champi_stt.assistant.ipc.structs import pack_wake_detected, unpack_wake_detected

def test_shared_memory_lifecycle():
    mgr = AssistantSharedMemoryManager(name_prefix="test_champi")
    mgr.create_regions()

    # Write signal
    data = pack_wake_detected(seq_num=1, wake_word="hey_jarvis")
    mgr.write_signal(AssistantSignalType.WAKE_DETECTED, data)

    # Read back
    read_data = mgr.read_signal(AssistantSignalType.WAKE_DETECTED)
    unpacked = unpack_wake_detected(read_data)
    assert unpacked["wake_word"] == "hey_jarvis"

    mgr.cleanup()
```

### Integration Tests

```python
def test_signal_flow():
    # Start daemon components
    signal_mgr = AssistantSignalManager()
    memory_mgr = AssistantSharedMemoryManager(name_prefix="test")
    memory_mgr.create_regions()

    processor = AssistantSignalProcessor(memory_mgr)
    processor.connect_signal(
        signal_mgr.processing,
        AssistantSignalType.WAKE_DETECTED,
        data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")}
    )
    processor.start()

    # Emit signal
    signal_mgr.processing.send(
        event_type="processing",
        sub_event="WAKE_DETECTED",
        data={"wake_word": "test"}
    )

    # Give processor time to process
    time.sleep(0.1)

    # Read from memory
    data = memory_mgr.read_signal(AssistantSignalType.WAKE_DETECTED)
    unpacked = unpack_wake_detected(data)
    assert unpacked["wake_word"] == "test"

    processor.stop()
    memory_mgr.cleanup()
```

### Manual UI Testing

```bash
# Terminal 1: Start daemon
champi-stt assistant run

# Terminal 2: Monitor UI logs
tail -f ~/.cache/champi_stt/ui.log

# Terminal 3: Trigger wake word
champi-stt assistant test wake

# Observe UI visual state changes
```

---

## Advanced Topics

### Cross-Platform Considerations

**Linux/macOS**:
- Shared memory backed by `/dev/shm/` (Linux) or tmpfs (macOS)
- Standard POSIX shared memory API

**Windows**:
- Uses `multiprocessing.shared_memory` (Python 3.8+)
- Backed by Windows shared memory objects
- Same API, different underlying implementation

### Signal Manager Singleton Pattern

The `AssistantSignalManager` uses `champi_signals.BaseSignalManager` which enforces singleton:

```python
# Multiple calls return same instance
mgr1 = AssistantSignalManager()
mgr2 = AssistantSignalManager()
assert mgr1 is mgr2  # True
```

### ACK-Based Reliability

The ACK system ensures no signals are lost:

1. Writer increments sequence number on each write
2. Reader tracks last ACK'd sequence number
3. If gap detected (e.g., seq jumped from 5 to 8), reader logs warning
4. Signals are NOT re-sent (fire-and-forget model)

**Why fire-and-forget?**
- UI is for visual feedback only
- Missing one frame of animation is acceptable
- Critical state is always re-sent on next change

---

## Reference

### Key Files

- `champi_stt/assistant/ipc/structs.py` - Signal structs and serialization
- `champi_stt/assistant/ipc/shared_memory.py` - Memory manager
- `champi_stt/assistant/ipc/signal_processor.py` - Signal processor
- `champi_stt/assistant/ipc/signal_reader.py` - Signal reader (UI side)
- `champi_stt/assistant/ipc/signal_manager.py` - Signal manager
- `champi_stt/assistant/service/daemon.py` - Daemon integration
- `champi_stt/assistant/ui/wake_indicator_ui.py` - UI subprocess

### Dependencies

- `multiprocessing.shared_memory` (Python 3.8+)
- `blinker` (signals)
- `champi-signals` (BaseSignalManager)
- `struct` (binary serialization)

---

## Changelog

### v0.1.0 (2025-10-01)
- Initial IPC infrastructure implementation
- 6 signal types (STATE_CHANGE, WAKE_DETECTED, RECORDING, TRANSCRIBING, EXECUTING, ERROR)
- Binary struct-based communication
- ACK tracking for signal loss detection
- Configurable memory prefix for namespace isolation
- Environment variable configuration
- GLFW-based UI subprocess with 60 Hz polling

---

## See Also

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Overall project architecture
- [README.md](../README.md) - Getting started guide
- [champi-signals](https://github.com/divagnz/champi-signals) - Signal library documentation
