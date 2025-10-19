"""
IPC Infrastructure for Assistant
=================================

Provides inter-process communication between the assistant daemon and UI subprocess.

Overview
--------
The IPC system enables real-time, low-latency communication for visual feedback
during voice assistant operation. It uses binary-packed shared memory for efficient
cross-process data transfer.

Architecture
------------
The system consists of several key components:

1. **Signal Types** (AssistantSignalType):
   - STATE_CHANGE: General state transitions (idle, listening, etc.)
   - WAKE_DETECTED: Wake word detection events
   - RECORDING: Audio recording status
   - TRANSCRIBING: Speech transcription progress
   - EXECUTING: Command execution notifications
   - ERROR: Error events

2. **Signal Manager** (AssistantSignalManager):
   - Singleton pattern using champi-signals
   - Emits blinker signals: state, processing, error
   - Integrates with daemon workflow

3. **Shared Memory Manager** (AssistantSharedMemoryManager):
   - Creates/attaches memory regions (one per signal type)
   - Manages ACK regions for signal loss detection
   - Binary struct serialization for cross-process compatibility

4. **Signal Processor** (AssistantSignalProcessor):
   - Bridges blinker signals to shared memory
   - FIFO queue with configurable size (default 100)
   - Background thread for async processing
   - Data mappers for signal transformation

5. **Signal Reader** (AssistantSignalReader):
   - Polls shared memory for new signals
   - Dispatches to registered handlers
   - ACK tracking and signal loss detection

Basic Usage
-----------
**Daemon (Producer)**::

    from champi_stt.assistant.ipc import (
        AssistantSignalManager,
        AssistantSharedMemoryManager,
        AssistantSignalProcessor,
        AssistantSignalType,
    )

    # Initialize
    signal_mgr = AssistantSignalManager()
    memory_mgr = AssistantSharedMemoryManager(name_prefix="my_app")
    memory_mgr.create_regions()

    # Setup processor
    processor = AssistantSignalProcessor(memory_mgr)
    processor.connect_signal(
        signal_mgr.processing,
        AssistantSignalType.WAKE_DETECTED,
        data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")}
    )
    processor.start()

    # Emit signals
    signal_mgr.processing.send(
        event_type="processing",
        sub_event="WAKE_DETECTED",
        data={"wake_word": "hey_jarvis"}
    )

    # Cleanup
    processor.stop()
    memory_mgr.cleanup()

**UI Subprocess (Consumer)**::

    from champi_stt.assistant.ipc import AssistantSharedMemoryManager
    from champi_stt.assistant.ipc.signal_reader import AssistantSignalReader

    # Attach to existing regions
    memory_mgr = AssistantSharedMemoryManager(name_prefix="my_app")
    memory_mgr.attach_regions()

    # Setup reader
    reader = AssistantSignalReader(memory_mgr)

    def on_wake(signal_data):
        print(f"Wake word: {signal_data.data['wake_word']}")

    reader.register_handler(AssistantSignalType.WAKE_DETECTED, on_wake)

    # Poll loop (60 Hz)
    while running:
        reader.poll_once()
        time.sleep(1/60)

    # Cleanup
    reader.stop()
    memory_mgr.cleanup()

Utilities
---------
**Cleanup orphaned regions**::

    from champi_stt.assistant.ipc import cleanup_orphaned_regions

    # Clean up memory left by crashed processes
    cleaned = cleanup_orphaned_regions(name_prefix="my_app")
    print(f"Cleaned {len(cleaned)} regions")

Configuration
-------------
Environment variables:
- CHAMPI_ASSISTANT_MEMORY_PREFIX: Namespace prefix (default: "champi_assistant")
- CHAMPI_ASSISTANT_UI_ENABLED: Enable UI subprocess (default: "true")
- CHAMPI_ASSISTANT_UI_WINDOW_X: UI window X position (default: "50")
- CHAMPI_ASSISTANT_UI_WINDOW_Y: UI window Y position (default: "50")

Performance
-----------
- Struct packing: ~1-5 μs per signal
- Memory write: ~10-50 μs
- Polling overhead: ~100-500 μs (60 Hz)
- Total latency: <1ms typical

See Also
--------
- docs/IPC.md: Comprehensive IPC documentation
- ARCHITECTURE.md: System architecture overview
"""

from champi_stt.assistant.ipc.shared_memory import (
    AssistantSharedMemoryManager,
    cleanup_orphaned_regions,
)
from champi_stt.assistant.ipc.signal_manager import AssistantSignalManager
from champi_stt.assistant.ipc.signal_processor import AssistantSignalProcessor
from champi_stt.assistant.ipc.structs import (
    AssistantSignalType,
    pack_state_change,
    pack_wake_detected,
    pack_recording,
    pack_transcribing,
    pack_executing,
    pack_error,
    unpack_state_change,
    unpack_wake_detected,
    unpack_recording,
    unpack_transcribing,
    unpack_executing,
    unpack_error,
)

__all__ = [
    "AssistantSignalManager",
    "AssistantSignalType",
    "AssistantSharedMemoryManager",
    "AssistantSignalProcessor",
    "cleanup_orphaned_regions",
    # Pack/unpack helpers
    "pack_state_change",
    "pack_wake_detected",
    "pack_recording",
    "pack_transcribing",
    "pack_executing",
    "pack_error",
    "unpack_state_change",
    "unpack_wake_detected",
    "unpack_recording",
    "unpack_transcribing",
    "unpack_executing",
    "unpack_error",
]
