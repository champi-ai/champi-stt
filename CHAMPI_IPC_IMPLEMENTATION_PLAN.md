# champi-ipc Library Extraction
## Comprehensive Implementation Plan

**Version**: 1.0
**Date**: 2025-10-19
**Status**: Ready for Implementation
**Estimated Effort**: 8 days
**Risk Level**: Low-Medium

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Code Duplication Analysis](#2-code-duplication-analysis)
3. [Architecture Design](#3-architecture-design)
4. [Detailed Implementation Steps](#4-detailed-implementation-steps)
5. [Code Examples](#5-code-examples)
6. [Testing Strategy](#6-testing-strategy)
7. [Migration Checklist](#7-migration-checklist)
8. [CLI Commands Specification](#8-cli-commands-specification)
9. [API Reference](#9-api-reference)
10. [Risk Assessment](#10-risk-assessment)
11. [Success Metrics](#11-success-metrics)
12. [Timeline & Milestones](#12-timeline--milestones)
13. [Appendices](#13-appendices)

---

## 1. Executive Summary

### 1.1 Recommendation

**EXTRACT to standalone `champi-ipc` library** ✅

### 1.2 ROI Analysis

| Metric | Current State | After Extraction | Improvement |
|--------|---------------|------------------|-------------|
| **Code Duplication** | ~600 lines duplicated | 0 duplicated | -100% |
| **Lines of IPC Code** | champi: 839<br>champi-stt: 1156<br>**Total: 1995** | champi-ipc: 800<br>champi: 203<br>champi-stt: 350<br>**Total: 1353** | **-32% (-642 lines)** |
| **Maintenance Burden** | Bug fixes need 2x work | Single fix applies to both | -50% |
| **Test Coverage** | Separate test suites | Shared comprehensive tests | +40% |
| **Time to Add Service** | 3-4 days (copy+modify) | 1-2 hours (import+configure) | -90% |

### 1.3 Benefits

**Technical:**
- ✅ Single source of truth for IPC logic
- ✅ Shared bug fixes and improvements
- ✅ Centralized cleanup utilities
- ✅ Easier to test infrastructure independently
- ✅ Type-safe generic implementation
- ✅ Dynamic lane creation support

**Operational:**
- ✅ Faster development of new IPC-based services
- ✅ Consistent IPC behavior across all services
- ✅ Reduced maintenance overhead
- ✅ Better documentation (one place)

**Future-Proofing:**
- ✅ Easy to add new services (TTS, STT, Vision, etc.)
- ✅ Can add features once, benefit everywhere
- ✅ Monitoring and metrics built-in

### 1.4 Costs

- **Development Time**: 8 days initial extraction + migration
- **Additional Dependency**: Services depend on champi-ipc package
- **Version Management**: Need to coordinate releases
- **Breaking Changes**: Could affect multiple services

**Verdict**: Benefits significantly outweigh costs

---

## 2. Code Duplication Analysis

### 2.1 Identical Code (~70% overlap)

#### File Comparison Matrix

| File | champi Lines | champi-stt Lines | Identical % | Notes |
|------|--------------|------------------|-------------|-------|
| **signal_queue.py** | 72 | 72 | **100%** | Completely identical |
| **shared_memory_manager.py** | 208 | 280 | **75%** | Core logic same, champi-stt has cleanup utils |
| **signal_processor.py** | 140 | 150 | **85%** | Same pattern, different signal enum |
| **signal_reader.py** | 100 | 110 | **80%** | Same pattern, different signal enum |
| **structs.py** | 203 | 350 | **0%** | Service-specific (TTS vs Assistant signals) |
| **Integration** | 100 | 120 | **50%** | Service-specific signal manager integration |
| **Total** | **839** | **1156** | **~70%** | ~600 lines duplicated |

### 2.2 Line-by-Line Analysis

#### SignalQueue - 100% Identical (72 lines)

**champi/signal_queue.py** vs **champi-stt/signal_queue.py**
```python
# IDENTICAL - No differences at all
class SignalQueue:
    def __init__(self, maxsize: int = 100):
        self.maxsize = maxsize
        self._queue = deque(maxlen=maxsize)
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._sequence_counter = 0
    # ... rest identical
```

**Extraction Plan**: Copy as-is, no changes needed

#### SharedMemoryManager - 75% Identical (156/208 lines)

**Identical sections:**
```python
# Lines 26-90: create_regions() - 100% identical logic
# Lines 91-119: attach_regions() - 100% identical
# Lines 120-145: write_signal() & read_signal() - 100% identical
# Lines 146-166: write_ack() & read_ack() - 100% identical
# Lines 167-208: cleanup() - 100% identical
```

**Differences:**
- champi-stt has `cleanup_orphaned_regions()` utility function (lines 18-61)
- champi uses hardcoded "champi_ipc", champi-stt supports custom prefix
- champi-stt has better docstrings

**Extraction Plan**:
- Use champi-stt version as base (has more features)
- Make signal type generic (type parameter)
- Extract cleanup utility to separate module

#### SignalProcessor - 85% Identical (119/140 lines)

**Identical sections:**
```python
# Lines 19-62: connect_signal() - 100% identical pattern
# Lines 63-86: start() & stop() - 100% identical
# Lines 87-124: _process_loop() - 100% identical
# Lines 125-140: disconnect_all() - 100% identical
```

**Differences:**
- Only difference is SignalType enum import
- champi-stt has slightly better type hints

**Extraction Plan**:
- Make signal_type parameter generic
- Use Protocol for signal type interface

#### SignalReader - 80% Identical (80/100 lines)

**Identical sections:**
```python
# Lines 18-67: poll_once() - 100% identical logic
# Lines 68-100: poll_loop() & stop() - 100% identical
```

**Differences:**
- Only SignalType enum import differs
- Struct unpacking calls differ (but pattern identical)

**Extraction Plan**:
- Make signal type generic
- Abstract struct unpacking via registry

### 2.3 Service-Specific Code (30%)

#### structs.py - 0% Identical (Completely Different)

**champi TTS signals:**
```python
class SignalType(IntEnum):
    VOICE_START = 1
    VOICE_STOP = 2
    LISTENING_START = 3
    LISTENING_STOP = 4
    PROCESSING_START = 5
    UPDATE_STATUS = 6
    SHUTDOWN = 7
    UI_LIFECYCLE = 8
```

**champi-stt Assistant signals:**
```python
class AssistantSignalType(IntEnum):
    STATE_CHANGE = 1
    WAKE_DETECTED = 2
    RECORDING = 3
    TRANSCRIBING = 4
    EXECUTING = 5
    ERROR = 6
```

**Extraction Plan**:
- Keep structs.py in each service
- Create Protocol for signal type enum
- Services define their own signal types

---

## 3. Architecture Design

### 3.1 champi-ipc Library Structure

```
champi-ipc/
├── src/
│   └── champi_ipc/
│       ├── __init__.py              # Public API exports
│       ├── core/
│       │   ├── __init__.py
│       │   ├── shared_memory.py     # Generic SharedMemoryManager
│       │   ├── signal_processor.py  # Generic SignalProcessor
│       │   ├── signal_reader.py     # Generic SignalReader
│       │   └── signal_queue.py      # FIFO queue (unchanged)
│       ├── base/
│       │   ├── __init__.py
│       │   ├── protocols.py         # SignalType Protocol, StructRegistry
│       │   └── exceptions.py        # Custom exceptions
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── cleanup.py           # cleanup_orphaned_regions()
│       │   ├── status.py            # list_regions(), get_region_info()
│       │   └── ack.py               # pack_ack(), unpack_ack()
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py              # Click CLI entry point
│       │   ├── cleanup_cmd.py       # cleanup command
│       │   ├── status_cmd.py        # status command
│       │   └── test_ui_cmd.py       # test-ui command
│       └── py.typed                 # PEP 561 marker
├── tests/
│   ├── __init__.py
│   ├── test_shared_memory.py
│   ├── test_signal_processor.py
│   ├── test_signal_reader.py
│   ├── test_signal_queue.py
│   ├── test_struct_registry.py
│   ├── test_cleanup_utils.py
│   ├── test_cli_cleanup.py
│   ├── test_cli_status.py
│   └── integration/
│       ├── __init__.py
│       ├── test_full_signal_flow.py
│       └── test_multi_process.py
├── examples/
│   ├── basic_usage.py
│   ├── custom_signals.py
│   └── multiple_services.py
├── docs/
│   ├── api.md
│   ├── migration_guide.md
│   └── troubleshooting.md
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── pre-commit.yml
│       └── release.yml
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── .pre-commit-config.yaml
```

### 3.2 Generic Core Classes

#### 3.2.1 SignalType Protocol

```python
# src/champi_ipc/base/protocols.py
from typing import Protocol, runtime_checkable
from enum import IntEnum

@runtime_checkable
class SignalTypeProtocol(Protocol):
    """Protocol for signal type enums.

    Any IntEnum can be used as a signal type as long as it follows
    this protocol (which IntEnum naturally does).
    """
    name: str
    value: int

    def __int__(self) -> int: ...


class StructRegistry:
    """Registry for mapping signal types to struct definitions.

    Allows services to register custom signal types with their
    pack/unpack functions and struct sizes.
    """

    def __init__(self):
        self._struct_sizes: dict[int, int] = {}
        self._pack_funcs: dict[int, callable] = {}
        self._unpack_funcs: dict[int, callable] = {}

    def register(
        self,
        signal_type: SignalTypeProtocol,
        struct_size: int,
        pack_func: callable,
        unpack_func: callable
    ):
        """Register a signal type with its struct operations.

        Args:
            signal_type: Signal type enum value
            struct_size: Size of packed struct in bytes
            pack_func: Function(seq_num, **kwargs) -> bytes
            unpack_func: Function(bytes) -> SignalData
        """
        type_id = int(signal_type)
        self._struct_sizes[type_id] = struct_size
        self._pack_funcs[type_id] = pack_func
        self._unpack_funcs[type_id] = unpack_func

    def get_struct_size(self, signal_type: SignalTypeProtocol) -> int:
        """Get struct size for signal type."""
        return self._struct_sizes[int(signal_type)]

    def pack(self, signal_type: SignalTypeProtocol, seq_num: int, **kwargs) -> bytes:
        """Pack signal using registered function."""
        return self._pack_funcs[int(signal_type)](seq_num, **kwargs)

    def unpack(self, signal_type: SignalTypeProtocol, data: bytes):
        """Unpack signal using registered function."""
        return self._unpack_funcs[int(signal_type)](data)
```

#### 3.2.2 Generic SharedMemoryManager

```python
# src/champi_ipc/core/shared_memory.py
from typing import TypeVar, Type
from enum import IntEnum
from multiprocessing import shared_memory

from champi_ipc.base.protocols import SignalTypeProtocol, StructRegistry
from champi_ipc.utils.ack import pack_ack, unpack_ack, get_ack_size

SignalT = TypeVar('SignalT', bound=SignalTypeProtocol)


class SharedMemoryManager:
    """Generic shared memory manager for any signal type enum.

    This class manages dedicated memory regions for each signal type,
    supporting data regions and ACK regions for signal loss detection.

    Type Parameters:
        SignalT: IntEnum type defining signal types

    Example:
        >>> from enum import IntEnum
        >>> class MySignals(IntEnum):
        ...     SIGNAL_A = 1
        ...     SIGNAL_B = 2
        >>>
        >>> # Create registry
        >>> registry = StructRegistry()
        >>> registry.register(MySignals.SIGNAL_A, 32, pack_a, unpack_a)
        >>>
        >>> # Create manager
        >>> mgr = SharedMemoryManager(
        ...     name_prefix="my_service",
        ...     signal_type_enum=MySignals,
        ...     struct_registry=registry
        ... )
        >>> mgr.create_regions()
    """

    def __init__(
        self,
        name_prefix: str,
        signal_type_enum: Type[SignalT],
        struct_registry: StructRegistry
    ):
        """Initialize shared memory manager.

        Args:
            name_prefix: Prefix for shared memory region names
            signal_type_enum: Enum class defining signal types
            struct_registry: Registry mapping signals to struct operations
        """
        self.name_prefix = name_prefix
        self.signal_type_enum = signal_type_enum
        self.registry = struct_registry
        self.memory_regions: dict[SignalT, shared_memory.SharedMemory] = {}
        self.ack_regions: dict[SignalT, shared_memory.SharedMemory] = {}
        self.is_creator = False

    def create_regions(self):
        """Create shared memory regions for all signal types (data + ACK).

        Creates two regions per signal type:
        - Data region: Stores packed signal struct
        - ACK region: Stores sequence number of last processed signal

        Raises:
            FileExistsError: If regions already exist (need cleanup first)
            PermissionError: If insufficient permissions to create regions
        """
        self.is_creator = True

        for signal_type in self.signal_type_enum:
            # Create data region
            region_name = f"{self.name_prefix}_{signal_type.name.lower()}"
            size = self.registry.get_struct_size(signal_type)

            try:
                # Try to unlink existing (cleanup from previous run)
                try:
                    existing = shared_memory.SharedMemory(name=region_name)
                    existing.close()
                    existing.unlink()
                except FileNotFoundError:
                    pass

                # Create new region
                shm = shared_memory.SharedMemory(
                    name=region_name, create=True, size=size
                )

                # Initialize with zeros
                shm.buf[:] = bytes(size)

                self.memory_regions[signal_type] = shm
                logger.debug(
                    f"Created shared memory region: {region_name} ({size} bytes)"
                )

            except Exception as e:
                logger.error(f"Failed to create region {region_name}: {e}")
                raise

            # Create ACK region
            ack_region_name = f"{self.name_prefix}_{signal_type.name.lower()}_ack"
            ack_size = get_ack_size()

            try:
                # Try to unlink existing
                try:
                    existing = shared_memory.SharedMemory(name=ack_region_name)
                    existing.close()
                    existing.unlink()
                except FileNotFoundError:
                    pass

                # Create new ACK region
                ack_shm = shared_memory.SharedMemory(
                    name=ack_region_name, create=True, size=ack_size
                )

                # Initialize with zeros
                ack_shm.buf[:] = bytes(ack_size)

                self.ack_regions[signal_type] = ack_shm
                logger.debug(f"Created ACK region: {ack_region_name} ({ack_size} bytes)")

            except Exception as e:
                logger.error(f"Failed to create ACK region {ack_region_name}: {e}")
                raise

    def attach_regions(self):
        """Attach to existing shared memory regions (data + ACK).

        Consumer processes call this instead of create_regions().

        Raises:
            FileNotFoundError: If regions don't exist (creator must create first)
        """
        self.is_creator = False

        for signal_type in self.signal_type_enum:
            # Attach to data region
            region_name = f"{self.name_prefix}_{signal_type.name.lower()}"

            try:
                shm = shared_memory.SharedMemory(name=region_name)
                self.memory_regions[signal_type] = shm
                logger.debug(f"Attached to region: {region_name}")
            except FileNotFoundError:
                logger.error(f"Region not found: {region_name}")
                raise

            # Attach to ACK region
            ack_region_name = f"{self.name_prefix}_{signal_type.name.lower()}_ack"

            try:
                ack_shm = shared_memory.SharedMemory(name=ack_region_name)
                self.ack_regions[signal_type] = ack_shm
                logger.debug(f"Attached to ACK region: {ack_region_name}")
            except FileNotFoundError:
                logger.error(f"ACK region not found: {ack_region_name}")
                raise

    def write_signal(self, signal_type: SignalT, data: bytes):
        """Write signal data to appropriate memory region.

        Args:
            signal_type: Type of signal
            data: Packed signal data (must match struct size)

        Raises:
            ValueError: If signal type not registered or data size mismatch
        """
        if signal_type not in self.memory_regions:
            raise ValueError(f"No memory region for: {signal_type}")

        shm = self.memory_regions[signal_type]
        expected_size = self.registry.get_struct_size(signal_type)

        if len(data) != expected_size:
            raise ValueError(
                f"Data size mismatch: expected {expected_size}, got {len(data)}"
            )

        # Atomic write to shared memory
        shm.buf[:expected_size] = data

    def read_signal(self, signal_type: SignalT) -> bytes:
        """Read signal data from memory region.

        Args:
            signal_type: Type of signal

        Returns:
            Packed signal data

        Raises:
            ValueError: If signal type not registered
        """
        if signal_type not in self.memory_regions:
            raise ValueError(f"No memory region for: {signal_type}")

        shm = self.memory_regions[signal_type]
        size = self.registry.get_struct_size(signal_type)

        return bytes(shm.buf[:size])

    def write_ack(self, signal_type: SignalT, seq_num: int):
        """Write ACK with sequence number to ACK region.

        Called by reader after successfully processing a signal.

        Args:
            signal_type: Type of signal
            seq_num: Sequence number to acknowledge
        """
        if signal_type not in self.ack_regions:
            raise ValueError(f"No ACK region for: {signal_type}")

        ack_data = pack_ack(seq_num)
        ack_shm = self.ack_regions[signal_type]
        ack_shm.buf[:len(ack_data)] = ack_data

    def read_ack(self, signal_type: SignalT) -> int:
        """Read ACK sequence number from ACK region.

        Used by processor to detect signal loss.

        Args:
            signal_type: Type of signal

        Returns:
            Last acknowledged sequence number
        """
        if signal_type not in self.ack_regions:
            raise ValueError(f"No ACK region for: {signal_type}")

        ack_shm = self.ack_regions[signal_type]
        ack_size = get_ack_size()
        ack_data = bytes(ack_shm.buf[:ack_size])
        return unpack_ack(ack_data)

    def cleanup(self):
        """Close and optionally unlink shared memory regions.

        If this instance created the regions (create_regions() was called),
        the regions will be unlinked. Otherwise they're just closed.
        """
        # Cleanup data regions
        for signal_type, shm in self.memory_regions.items():
            try:
                shm.close()

                if self.is_creator:
                    shm.unlink()
                    logger.debug(
                        f"Cleaned up region: {self.name_prefix}_{signal_type.name.lower()}"
                    )
            except Exception as e:
                logger.error(f"Error cleaning up {signal_type}: {e}")

        self.memory_regions.clear()

        # Cleanup ACK regions
        for signal_type, ack_shm in self.ack_regions.items():
            try:
                ack_shm.close()

                if self.is_creator:
                    ack_shm.unlink()
                    logger.debug(
                        f"Cleaned up ACK region: {self.name_prefix}_{signal_type.name.lower()}_ack"
                    )
            except Exception as e:
                logger.error(f"Error cleaning up ACK for {signal_type}: {e}")

        self.ack_regions.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
```

#### 3.2.3 Generic SignalProcessor

```python
# src/champi_ipc/core/signal_processor.py
import threading
from typing import Optional, TypeVar, Callable, Type

from blinker import Signal
from loguru import logger

from champi_ipc.core.shared_memory import SharedMemoryManager
from champi_ipc.core.signal_queue import SignalQueue
from champi_ipc.base.protocols import SignalTypeProtocol

SignalT = TypeVar('SignalT', bound=SignalTypeProtocol)


class SignalProcessor:
    """Bridges blinker signals to shared memory via FIFO queue.

    This class connects to blinker signals, queues them in a thread-safe
    FIFO queue, and processes them in a background thread, writing to
    shared memory.

    Type Parameters:
        SignalT: IntEnum type defining signal types

    Example:
        >>> from blinker import signal
        >>>
        >>> # Create processor
        >>> processor = SignalProcessor(memory_manager)
        >>>
        >>> # Connect signals
        >>> my_signal = signal('my-signal')
        >>> processor.connect_signal(
        ...     my_signal,
        ...     MySignals.SIGNAL_A,
        ...     data_mapper=lambda text: {'text': text}
        ... )
        >>>
        >>> # Start processing
        >>> processor.start()
        >>>
        >>> # Emit signal (will be queued and written to shared memory)
        >>> my_signal.send(text="Hello")
    """

    def __init__(self, memory_manager: SharedMemoryManager):
        """Initialize signal processor.

        Args:
            memory_manager: Shared memory manager for writing signals
        """
        self.memory_manager = memory_manager
        self.queue = SignalQueue(maxsize=100)
        self.running = False
        self.processor_thread: Optional[threading.Thread] = None
        self.connected_signals = []

    def connect_signal(
        self,
        signal: Signal,
        signal_type: SignalT,
        data_mapper: Optional[Callable] = None
    ):
        """Connect a blinker signal to the processor.

        Args:
            signal: Blinker signal to connect
            signal_type: Signal type enum value
            data_mapper: Optional function to map signal kwargs to queue data
                        Signature: (sender, **kwargs) -> dict | None
                        Return None to skip queueing this signal

        Example:
            >>> # Simple mapper extracting specific fields
            >>> def mapper(text, **kwargs):
            ...     return {'text': text[:100]}  # Truncate to 100 chars
            >>>
            >>> processor.connect_signal(my_signal, MySignals.TEXT, mapper)
        """
        def signal_handler(sender, **kwargs):
            # Map signal data if mapper provided
            if data_mapper:
                queue_data = data_mapper(**kwargs)
                # Skip if mapper returns None
                if queue_data is None:
                    return
            else:
                queue_data = kwargs

            # Add to queue
            seq_num = self.queue.put(signal_type, **queue_data)
            logger.debug(
                f"Queued {signal_type.name} (seq: {seq_num}, queue: {self.queue.size()})"
            )

        signal.connect(signal_handler, weak=False)
        self.connected_signals.append((signal, signal_handler))

        logger.info(f"Connected signal processor for {signal_type.name}")

    def start(self):
        """Start processing signals from queue.

        Launches background thread that pulls from queue and writes to
        shared memory.
        """
        if self.running:
            logger.warning("Signal processor already running")
            return

        self.running = True
        self.processor_thread = threading.Thread(
            target=self._process_loop, daemon=True, name="SignalProcessor"
        )
        self.processor_thread.start()

        logger.info("Signal processor started")

    def stop(self):
        """Stop processing signals.

        Waits up to 2 seconds for processor thread to finish current item.
        """
        self.running = False

        if self.processor_thread:
            self.processor_thread.join(timeout=2.0)
            self.processor_thread = None

        logger.info("Signal processor stopped")

    def _process_loop(self):
        """Main processing loop - pulls from queue and writes to shared memory.

        Runs in background thread until stop() is called.
        """
        while self.running:
            # Get next item from queue (blocks with timeout)
            item = self.queue.get(timeout=0.5)

            if item is None:
                continue  # Timeout, check if still running

            try:
                # Check ACK to detect missed signals
                ack_seq = self.memory_manager.read_ack(item.signal_type)
                expected_ack = item.seq_num - 1

                if ack_seq < expected_ack:
                    missed_count = expected_ack - ack_seq
                    logger.warning(
                        f"⚠️  Signal loss for {item.signal_type.name}: "
                        f"Reader at {ack_seq}, writing {item.seq_num} "
                        f"({missed_count} signals skipped)"
                    )

                # Pack signal data into binary struct
                packed_data = self.memory_manager.registry.pack(
                    item.signal_type, item.seq_num, **item.data
                )

                # Write to shared memory
                self.memory_manager.write_signal(item.signal_type, packed_data)

                logger.debug(
                    f"Wrote {item.signal_type.name} to shared memory (seq: {item.seq_num})"
                )

            except Exception as e:
                logger.error(f"Error processing {item.signal_type.name}: {e}")

    def disconnect_all(self):
        """Disconnect all signal handlers."""
        for signal, handler in self.connected_signals:
            signal.disconnect(handler)

        self.connected_signals.clear()
        logger.info("Disconnected all signal handlers")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        self.disconnect_all()
```

#### 3.2.4 Generic SignalReader

```python
# src/champi_ipc/core/signal_reader.py
import time
from typing import Callable, TypeVar, Type

from loguru import logger

from champi_ipc.core.shared_memory import SharedMemoryManager
from champi_ipc.base.protocols import SignalTypeProtocol

SignalT = TypeVar('SignalT', bound=SignalTypeProtocol)


class SignalReader:
    """Reads signals from shared memory and dispatches to handlers.

    Consumer process (e.g., UI) uses this to poll for new signals
    and process them.

    Type Parameters:
        SignalT: IntEnum type defining signal types

    Example:
        >>> # Create reader
        >>> reader = SignalReader(memory_manager)
        >>>
        >>> # Register handlers
        >>> def handle_text(signal_data):
        ...     print(f"Text: {signal_data.data['text']}")
        >>>
        >>> reader.register_handler(MySignals.TEXT, handle_text)
        >>>
        >>> # Poll loop
        >>> reader.poll_loop(poll_rate_hz=60)
    """

    def __init__(self, memory_manager: SharedMemoryManager):
        """Initialize signal reader.

        Args:
            memory_manager: Shared memory manager for reading signals
        """
        self.memory_manager = memory_manager
        self.handlers: dict[SignalT, Callable] = {}
        self.last_seq_nums: dict[SignalT, int] = {
            st: 0 for st in memory_manager.signal_type_enum
        }
        self.running = False

    def register_handler(self, signal_type: SignalT, handler: Callable):
        """Register a handler function for a signal type.

        Args:
            signal_type: Signal type to handle
            handler: Callback function
                    Signature: (signal_data: SignalData) -> None

        Example:
            >>> def my_handler(signal_data):
            ...     print(f"Seq: {signal_data.seq_num}")
            ...     print(f"Type: {signal_data.signal_type}")
            ...     print(f"Data: {signal_data.data}")
            >>>
            >>> reader.register_handler(MySignals.TEXT, my_handler)
        """
        self.handlers[signal_type] = handler
        logger.info(f"Registered handler for {signal_type.name}")

    def poll_once(self):
        """Poll all signal regions once and dispatch any new signals.

        Call this repeatedly in your main loop, or use poll_loop().
        """
        for signal_type in self.memory_manager.signal_type_enum:
            try:
                # Read from shared memory
                raw_data = self.memory_manager.read_signal(signal_type)

                # Check if memory is uninitialized (signal_type byte is 0)
                if raw_data[8] == 0:
                    continue  # Skip uninitialized memory

                # Unpack struct
                signal_data = self.memory_manager.registry.unpack(
                    signal_type, raw_data
                )

                # Check if this is a new signal
                if signal_data.seq_num > self.last_seq_nums[signal_type]:
                    self.last_seq_nums[signal_type] = signal_data.seq_num

                    # Dispatch to handler if registered
                    if signal_type in self.handlers:
                        self.handlers[signal_type](signal_data)
                        logger.debug(
                            f"Dispatched {signal_type.name} (seq: {signal_data.seq_num})"
                        )

                    # Write ACK after processing
                    self.memory_manager.write_ack(signal_type, signal_data.seq_num)
                    logger.debug(f"ACKed {signal_type.name} (seq: {signal_data.seq_num})")

            except Exception as e:
                logger.error(f"Error reading {signal_type.name}: {e}")

    def poll_loop(self, poll_rate_hz: int = 60):
        """Continuously poll for new signals.

        Args:
            poll_rate_hz: Polling frequency in Hz (default 60)

        Blocks until stop() is called.
        """
        self.running = True
        poll_interval = 1.0 / poll_rate_hz

        logger.info(f"Starting poll loop at {poll_rate_hz} Hz")

        while self.running:
            start_time = time.time()

            self.poll_once()

            # Sleep to maintain poll rate
            elapsed = time.time() - start_time
            sleep_time = max(0, poll_interval - elapsed)
            time.sleep(sleep_time)

        logger.info("Poll loop stopped")

    def stop(self):
        """Stop the poll loop."""
        self.running = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
```

### 3.3 Utility Modules

#### 3.3.1 Cleanup Utilities

```python
# src/champi_ipc/utils/cleanup.py
from typing import List, Type
from multiprocessing import shared_memory

from loguru import logger

from champi_ipc.base.protocols import SignalTypeProtocol


def cleanup_orphaned_regions(
    name_prefix: str,
    signal_type_enum: Type[SignalTypeProtocol]
) -> List[str]:
    """Clean up orphaned shared memory regions.

    Removes regions left behind by crashed processes or improper shutdowns.
    Safe to call even if regions don't exist.

    Args:
        name_prefix: Memory region prefix to clean up
        signal_type_enum: Enum defining signal types

    Returns:
        List of cleaned region names

    Example:
        >>> from my_service import MySignals
        >>> cleaned = cleanup_orphaned_regions("my_service", MySignals)
        >>> print(f"Cleaned {len(cleaned)} regions")
    """
    cleaned_regions = []

    for signal_type in signal_type_enum:
        # Try to clean up data region
        region_name = f"{name_prefix}_{signal_type.name.lower()}"
        try:
            shm = shared_memory.SharedMemory(name=region_name)
            shm.close()
            shm.unlink()
            cleaned_regions.append(region_name)
            logger.info(f"Cleaned up orphaned region: {region_name}")
        except FileNotFoundError:
            pass  # Region doesn't exist, skip
        except Exception as e:
            logger.warning(f"Failed to clean up {region_name}: {e}")

        # Try to clean up ACK region
        ack_region_name = f"{name_prefix}_{signal_type.name.lower()}_ack"
        try:
            ack_shm = shared_memory.SharedMemory(name=ack_region_name)
            ack_shm.close()
            ack_shm.unlink()
            cleaned_regions.append(ack_region_name)
            logger.info(f"Cleaned up orphaned ACK region: {ack_region_name}")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"Failed to clean up {ack_region_name}: {e}")

    return cleaned_regions


def list_regions(name_prefix: str) -> List[str]:
    """List all shared memory regions with given prefix.

    Args:
        name_prefix: Region prefix to search for

    Returns:
        List of region names

    Note:
        This function relies on OS-specific mechanisms:
        - Linux: /dev/shm/
        - macOS/BSD: /var/tmp/
        - Windows: Global\\ namespace
    """
    import os
    import platform

    regions = []

    system = platform.system()

    if system == "Linux":
        shm_dir = "/dev/shm"
        if os.path.exists(shm_dir):
            for filename in os.listdir(shm_dir):
                if filename.startswith(name_prefix):
                    regions.append(filename)

    elif system == "Darwin":  # macOS
        # macOS uses /var/tmp for POSIX shared memory
        # Names are prefixed with "sem."
        pass  # TODO: Implement macOS listing

    elif system == "Windows":
        # Windows uses Global\\ namespace
        pass  # TODO: Implement Windows listing

    return regions


def get_region_info(region_name: str) -> dict:
    """Get information about a shared memory region.

    Args:
        region_name: Name of the region

    Returns:
        Dictionary with region info:
        - name: Region name
        - size: Size in bytes
        - exists: Whether region exists
        - accessible: Whether we can access it

    Example:
        >>> info = get_region_info("my_service_signal_a")
        >>> print(f"Size: {info['size']} bytes")
    """
    info = {
        "name": region_name,
        "size": 0,
        "exists": False,
        "accessible": False
    }

    try:
        shm = shared_memory.SharedMemory(name=region_name)
        info["size"] = shm.size
        info["exists"] = True
        info["accessible"] = True
        shm.close()
    except FileNotFoundError:
        info["exists"] = False
    except PermissionError:
        info["exists"] = True
        info["accessible"] = False
    except Exception as e:
        logger.warning(f"Error getting info for {region_name}: {e}")

    return info
```

#### 3.3.2 ACK Utilities

```python
# src/champi_ipc/utils/ack.py
import struct

# ACK struct: seq_num(Q) - just the sequence number
ACK_STRUCT = struct.Struct("=Q")


def pack_ack(seq_num: int) -> bytes:
    """Pack ACK with sequence number.

    Args:
        seq_num: Sequence number to acknowledge

    Returns:
        Packed ACK data (8 bytes)
    """
    return ACK_STRUCT.pack(seq_num)


def unpack_ack(data: bytes) -> int:
    """Unpack ACK to get sequence number.

    Args:
        data: Packed ACK data

    Returns:
        Sequence number
    """
    return ACK_STRUCT.unpack(data)[0]


def get_ack_size() -> int:
    """Get the size of ACK struct in bytes.

    Returns:
        Size in bytes (always 8)
    """
    return ACK_STRUCT.size
```

### 3.4 Public API

```python
# src/champi_ipc/__init__.py
"""champi-ipc: Shared Memory IPC Infrastructure

A generic, reusable library for inter-process communication using
shared memory and blinker signals.

Example:
    >>> from champi_ipc import (
    ...     SharedMemoryManager,
    ...     SignalProcessor,
    ...     SignalReader,
    ...     StructRegistry,
    ...     cleanup_orphaned_regions
    ... )
    >>>
    >>> # Define your signal types
    >>> from enum import IntEnum
    >>> class MySignals(IntEnum):
    ...     SIGNAL_A = 1
    ...     SIGNAL_B = 2
    >>>
    >>> # Create registry
    >>> registry = StructRegistry()
    >>> registry.register(MySignals.SIGNAL_A, 32, pack_a, unpack_a)
    >>>
    >>> # Create manager
    >>> manager = SharedMemoryManager("my_app", MySignals, registry)
    >>> manager.create_regions()
"""

__version__ = "0.1.0"

# Core classes
from champi_ipc.core.shared_memory import SharedMemoryManager
from champi_ipc.core.signal_processor import SignalProcessor
from champi_ipc.core.signal_reader import SignalReader
from champi_ipc.core.signal_queue import SignalQueue, SignalQueueItem

# Base protocols
from champi_ipc.base.protocols import SignalTypeProtocol, StructRegistry
from champi_ipc.base.exceptions import (
    IPCError,
    RegionNotFoundError,
    RegionExistsError,
    SignalTypeNotRegisteredError
)

# Utilities
from champi_ipc.utils.cleanup import (
    cleanup_orphaned_regions,
    list_regions,
    get_region_info
)
from champi_ipc.utils.ack import pack_ack, unpack_ack, get_ack_size

__all__ = [
    # Core
    "SharedMemoryManager",
    "SignalProcessor",
    "SignalReader",
    "SignalQueue",
    "SignalQueueItem",

    # Base
    "SignalTypeProtocol",
    "StructRegistry",

    # Exceptions
    "IPCError",
    "RegionNotFoundError",
    "RegionExistsError",
    "SignalTypeNotRegisteredError",

    # Utilities
    "cleanup_orphaned_regions",
    "list_regions",
    "get_region_info",
    "pack_ack",
    "unpack_ack",
    "get_ack_size",
]
```

---

## 4. Detailed Implementation Steps

### Phase 1: Repository Setup (Day 1)

**Duration**: 6-8 hours
**Prerequisites**: None
**Deliverable**: Fully configured GitHub repository with CI/CD

#### Step 1.1: Create GitHub Repository (30 minutes)

```bash
# 1. Create repo on GitHub
gh repo create champi-ipc --public --description "Shared memory IPC infrastructure"

# 2. Clone locally
git clone https://github.com/divagnz/champi-ipc.git
cd champi-ipc

# 3. Create initial structure
mkdir -p src/champi_ipc/{core,base,utils,cli}
mkdir -p tests/{unit,integration}
mkdir -p examples docs .github/workflows

# 4. Create __init__.py files
touch src/champi_ipc/__init__.py
touch src/champi_ipc/{core,base,utils,cli}/__init__.py
touch tests/__init__.py
touch tests/{unit,integration}/__init__.py
```

#### Step 1.2: Setup pyproject.toml (45 minutes)

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "champi-ipc"
version = "0.1.0"
description = "Shared memory IPC infrastructure for multi-process Python applications"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "Divagnz", email = "oscar.liguori.bagnis@gmail.com"}
]
requires-python = ">=3.12"
keywords = ["ipc", "shared-memory", "signals", "multiprocessing", "blinker"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: System :: Distributed Computing",
]

dependencies = [
    "loguru>=0.7.0",
    "blinker>=1.7.0",
    "click>=8.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.23.0",
    "mypy>=1.8.0",
    "ruff>=0.2.0",
    "black>=24.0.0",
    "pre-commit>=3.6.0",
]

[project.urls]
Homepage = "https://github.com/divagnz/champi-ipc"
Documentation = "https://github.com/divagnz/champi-ipc/blob/main/README.md"
Repository = "https://github.com/divagnz/champi-ipc"
Issues = "https://github.com/divagnz/champi-ipc/issues"

[project.scripts]
champi-ipc = "champi_ipc.cli.main:cli"

[tool.hatch.build.targets.wheel]
packages = ["src/champi_ipc"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--cov=src/champi_ipc",
    "--cov-report=term-missing",
    "--cov-report=html",
]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by black)
]

[tool.black]
line-length = 88
target-version = ['py312']
```

#### Step 1.3: Create LICENSE (5 minutes)

```text
MIT License

Copyright (c) 2025 Divagnz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

#### Step 1.4: Setup Pre-commit Hooks (30 minutes)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.2.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

Install hooks:
```bash
uv pip install pre-commit
pre-commit install
pre-commit run --all-files  # Test it works
```

#### Step 1.5: Setup CI/CD Workflows (90 minutes)

**Workflow 1: CI Pipeline**

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: |
          uv pip install -e ".[dev]"

      - name: Run ruff
        run: uv run ruff check src/

      - name: Run black check
        run: uv run black --check src/

      - name: Run mypy
        run: uv run mypy src/

  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.12', '3.13']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv pip install -e ".[dev]"

      - name: Run tests
        run: uv run pytest

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.12'
        with:
          files: ./coverage.xml

  build:
    runs-on: ubuntu-latest
    needs: [lint, test]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install build tools
        run: pip install build

      - name: Build package
        run: python -m build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
```

**Workflow 2: Pre-commit CI**

```yaml
# .github/workflows/pre-commit.yml
name: Pre-commit

on:
  pull_request:
  push:
    branches: [main]

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - uses: pre-commit/action@v3.0.0
```

**Workflow 3: Release to PyPI**

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install build tools
        run: pip install build twine

      - name: Build package
        run: python -m build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
          generate_release_notes: true
```

#### Step 1.6: Create README.md (60 minutes)

```markdown
# champi-ipc

[![CI](https://github.com/divagnz/champi-ipc/workflows/CI/badge.svg)](https://github.com/divagnz/champi-ipc/actions)
[![PyPI version](https://badge.fury.io/py/champi-ipc.svg)](https://badge.fury.io/py/champi-ipc)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Generic Shared Memory IPC Infrastructure for Python**

A lightweight, type-safe library for inter-process communication using shared memory and blinker signals.

---

## Features

- ✅ **Generic Design** - Works with any signal type enum
- ✅ **Type-Safe** - Full type hints and mypy support
- ✅ **Low Latency** - Binary struct serialization (~1ms overhead)
- ✅ **Signal Loss Detection** - ACK-based tracking
- ✅ **Thread-Safe** - FIFO queue for ordered processing
- ✅ **Cleanup Utilities** - Automatic orphaned region cleanup
- ✅ **CLI Tools** - status, cleanup, test-ui commands
- ✅ **Cross-Platform** - Linux, macOS, Windows

---

## Installation

```bash
pip install champi-ipc
```

Or with UV:
```bash
uv pip install champi-ipc
```

---

## Quick Start

### 1. Define Your Signal Types

```python
from enum import IntEnum
import struct

class MySignals(IntEnum):
    TEXT_MESSAGE = 1
    STATUS_UPDATE = 2

# Define struct formats
TEXT_STRUCT = struct.Struct("=QB256s")  # seq_num, signal_type, text
STATUS_STRUCT = struct.Struct("=QBB")   # seq_num, signal_type, status_code

# Pack/unpack functions
def pack_text(seq_num: int, text: str) -> bytes:
    text_bytes = text.encode()[:256].ljust(256, b'\x00')
    return TEXT_STRUCT.pack(seq_num, MySignals.TEXT_MESSAGE, text_bytes)

def unpack_text(data: bytes) -> dict:
    seq_num, signal_type, text_bytes = TEXT_STRUCT.unpack(data)
    return {"seq_num": seq_num, "text": text_bytes.rstrip(b'\x00').decode()}
```

### 2. Create Struct Registry

```python
from champi_ipc import StructRegistry

registry = StructRegistry()
registry.register(
    MySignals.TEXT_MESSAGE,
    TEXT_STRUCT.size,
    pack_text,
    unpack_text
)
```

### 3. Producer Process (Writer)

```python
from champi_ipc import SharedMemoryManager, SignalProcessor
from blinker import signal

# Create memory manager
manager = SharedMemoryManager("my_app", MySignals, registry)
manager.create_regions()

# Create signal processor
processor = SignalProcessor(manager)

# Connect blinker signal
text_signal = signal('text-message')
processor.connect_signal(
    text_signal,
    MySignals.TEXT_MESSAGE,
    data_mapper=lambda text: {'text': text}
)

# Start processing
processor.start()

# Emit signals (will be written to shared memory)
text_signal.send(text="Hello from producer!")

# Cleanup
processor.stop()
manager.cleanup()
```

### 4. Consumer Process (Reader)

```python
from champi_ipc import SharedMemoryManager, SignalReader

# Attach to existing regions
manager = SharedMemoryManager("my_app", MySignals, registry)
manager.attach_regions()

# Create reader
reader = SignalReader(manager)

# Register handler
def handle_text(signal_data):
    print(f"Received: {signal_data.data['text']}")

reader.register_handler(MySignals.TEXT_MESSAGE, handle_text)

# Poll loop (60 Hz)
reader.poll_loop(poll_rate_hz=60)

# Cleanup
manager.cleanup()
```

---

## CLI Commands

### Cleanup Orphaned Regions

```bash
champi-ipc cleanup --prefix my_app
```

### Show Region Status

```bash
champi-ipc status --prefix my_app
```

### Test UI (Standalone)

```bash
champi-ipc test-ui --prefix my_app
```

---

## Advanced Usage

See [examples/](examples/) for more detailed examples.

---

## Documentation

- [API Reference](docs/api.md)
- [Migration Guide](docs/migration_guide.md)
- [Troubleshooting](docs/troubleshooting.md)

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Acknowledgments

Built with:
- [blinker](https://github.com/pallets-eco/blinker) - Fast signals/events
- [loguru](https://github.com/Delgan/loguru) - Beautiful logging
- [click](https://click.pallets.com/) - CLI framework
```

#### Step 1.7: Create CHANGELOG.md (15 minutes)

```markdown
# Changelog

All notable changes to champi-ipc will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-01-XX

### Added
- Initial release
- Generic SharedMemoryManager with signal type protocols
- SignalProcessor for blinker → shared memory bridge
- SignalReader for shared memory → handlers
- SignalQueue for thread-safe FIFO processing
- StructRegistry for dynamic signal type registration
- Cleanup utilities for orphaned regions
- CLI commands (cleanup, status, test-ui)
- Comprehensive test suite
- Full type hints and mypy support
- CI/CD with GitHub Actions
- Cross-platform support (Linux, macOS, Windows)
```

#### Step 1.8: Create .gitignore (5 minutes)

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Secrets
.secrets.baseline
*.env
```

#### Step 1.9: Initial Commit (10 minutes)

```bash
# Initialize git
git init
git add .
git commit -m "chore: initial project structure"

# Create develop branch
git branch develop
git checkout develop

# Push to GitHub
git push -u origin main
git push -u origin develop

# Set up branch protection
gh api repos/divagnz/champi-ipc/branches/main/protection \
  --method PUT \
  --field required_status_checks[strict]=true \
  --field required_pull_request_reviews[required_approving_review_count]=1
```

---

### Phase 2: Code Extraction (Days 2-3)

**Duration**: 12-16 hours
**Prerequisites**: Phase 1 complete
**Deliverable**: All core classes extracted and working

#### Day 2: Extract Core Classes (Steps 2.1 - 2.10)

#### Step 2.1: Copy SignalQueue (20 minutes)

This file is 100% identical, just copy it:

```bash
# Copy from champi
cp /path/to/champi/mcp_champi/ipc_svc/signal_queue.py \
   src/champi_ipc/core/signal_queue.py

# Add imports
```

Edit `src/champi_ipc/core/signal_queue.py`:
```python
# Change import to use protocols
from champi_ipc.base.protocols import SignalTypeProtocol

# Update type hints
class SignalQueueItem:
    def __init__(self, signal_type: SignalTypeProtocol, seq_num: int, **kwargs):
        # ... rest unchanged
```

#### Step 2.2: Extract SharedMemoryManager (60 minutes)

Copy from champi-stt (has more features):

```bash
cp /path/to/champi-stt/src/champi_stt/assistant/ipc/shared_memory.py \
   src/champi_ipc/core/shared_memory.py
```

Make generic (see Section 3.2.2 for full code):

1. Add type parameters:
```python
from typing import TypeVar, Type
SignalT = TypeVar('SignalT', bound=SignalTypeProtocol)
```

2. Update `__init__`:
```python
def __init__(
    self,
    name_prefix: str,
    signal_type_enum: Type[SignalT],
    struct_registry: StructRegistry
):
```

3. Replace hardcoded struct calls with registry:
```python
# Before
size = get_struct_size(signal_type)

# After
size = self.registry.get_struct_size(signal_type)
```

4. Update all methods to use `signal_type_enum` instead of hardcoded enum

#### Step 2.3: Extract cleanup utility (30 minutes)

Move `cleanup_orphaned_regions()` to separate module:

```python
# src/champi_ipc/utils/cleanup.py
# See Section 3.3.1 for full code
```

Update imports in shared_memory.py to remove this function.

#### Step 2.4: Extract SignalProcessor (60 minutes)

Copy and make generic:

```bash
cp /path/to/champi/mcp_champi/ipc_svc/signal_processor.py \
   src/champi_ipc/core/signal_processor.py
```

Make generic (see Section 3.2.3 for full code):

1. Add type parameters
2. Update to use StructRegistry for packing
3. Remove hardcoded signal type references

#### Step 2.5: Extract SignalReader (60 minutes)

Copy and make generic:

```bash
cp /path/to/champi/mcp_champi/ipc_svc/signal_reader.py \
   src/champi_ipc/core/signal_reader.py
```

Make generic (see Section 3.2.4 for full code):

1. Add type parameters
2. Update to use StructRegistry for unpacking
3. Remove hardcoded signal type references

#### Step 2.6: Create Protocol Definition (45 minutes)

```python
# src/champi_ipc/base/protocols.py
# See Section 3.2.1 for full code

# Test it works:
from enum import IntEnum

class TestSignals(IntEnum):
    SIGNAL_A = 1

# Should pass type check
from champi_ipc.base.protocols import SignalTypeProtocol
assert isinstance(TestSignals.SIGNAL_A, SignalTypeProtocol)
```

#### Step 2.7: Create StructRegistry (60 minutes)

```python
# src/champi_ipc/base/protocols.py
# Add StructRegistry class (see Section 3.2.1)

# Write unit test
# tests/unit/test_struct_registry.py
import pytest
from champi_ipc.base.protocols import StructRegistry

def test_register_and_get_size():
    registry = StructRegistry()

    def pack(seq, **kw): return b'\x00' * 10
    def unpack(data): return {}

    registry.register(1, 10, pack, unpack)
    assert registry.get_struct_size(1) == 10

# Run test
uv run pytest tests/unit/test_struct_registry.py
```

#### Step 2.8: Create ACK Utilities (30 minutes)

```python
# src/champi_ipc/utils/ack.py
# See Section 3.3.2 for full code

# Write unit test
# tests/unit/test_ack.py
from champi_ipc.utils.ack import pack_ack, unpack_ack, get_ack_size

def test_pack_unpack_ack():
    seq_num = 42
    packed = pack_ack(seq_num)
    assert len(packed) == get_ack_size()
    assert unpack_ack(packed) == seq_num

uv run pytest tests/unit/test_ack.py
```

#### Step 2.9: Create Exception Classes (30 minutes)

```python
# src/champi_ipc/base/exceptions.py

class IPCError(Exception):
    """Base exception for IPC errors."""
    pass

class RegionNotFoundError(IPCError):
    """Shared memory region not found."""
    pass

class RegionExistsError(IPCError):
    """Shared memory region already exists."""
    pass

class SignalTypeNotRegisteredError(IPCError):
    """Signal type not registered in struct registry."""
    pass
```

#### Step 2.10: Update __init__.py (15 minutes)

```python
# src/champi_ipc/__init__.py
# See Section 3.4 for full code
```

**Day 2 Checkpoint**: Run all unit tests

```bash
uv run pytest tests/unit/
```

---

#### Day 3: Create CLI and Advanced Features (Steps 2.11 - 2.20)

#### Step 2.11: Create CLI Main Entry Point (45 minutes)

```python
# src/champi_ipc/cli/main.py
import click

@click.group()
@click.version_option()
def cli():
    """champi-ipc CLI - Shared memory IPC utilities."""
    pass

# Import commands
from champi_ipc.cli.cleanup_cmd import cleanup
from champi_ipc.cli.status_cmd import status

cli.add_command(cleanup)
cli.add_command(status)

if __name__ == "__main__":
    cli()
```

Test it works:
```bash
uv run champi-ipc --version
uv run champi-ipc --help
```

#### Step 2.12: Implement Cleanup Command (60 minutes)

```python
# src/champi_ipc/cli/cleanup_cmd.py
import click
from loguru import logger

from champi_ipc.utils.cleanup import cleanup_orphaned_regions


@click.command()
@click.option(
    '--prefix',
    default='champi_ipc',
    help='Memory region prefix to clean up'
)
@click.option(
    '--signal-module',
    required=True,
    help='Python module path to signal enum (e.g., my_app.signals.MySignals)'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be cleaned without actually cleaning'
)
def cleanup(prefix: str, signal_module: str, dry_run: bool):
    """Clean up orphaned shared memory regions.

    Example:
        champi-ipc cleanup --prefix my_app --signal-module my_app.signals.MySignals
    """
    import importlib

    try:
        # Import signal enum
        module_path, class_name = signal_module.rsplit('.', 1)
        module = importlib.import_module(module_path)
        signal_enum = getattr(module, class_name)

        logger.info(f"Cleaning up regions with prefix: {prefix}")

        if dry_run:
            logger.info("DRY RUN - No actual cleanup will be performed")
            # List regions without cleaning
            from champi_ipc.utils.cleanup import list_regions
            regions = list_regions(prefix)
            if regions:
                click.echo(f"Would clean {len(regions)} regions:")
                for region in regions:
                    click.echo(f"  - {region}")
            else:
                click.echo("No regions found to clean")
        else:
            cleaned = cleanup_orphaned_regions(prefix, signal_enum)

            if cleaned:
                click.echo(f"✅ Cleaned {len(cleaned)} regions:")
                for region in cleaned:
                    click.echo(f"  - {region}")
            else:
                click.echo("No orphaned regions found")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
```

Test:
```bash
# Create test signal enum
cat > test_signals.py <<EOF
from enum import IntEnum
class TestSignals(IntEnum):
    SIGNAL_A = 1
EOF

# Test dry run
uv run champi-ipc cleanup --prefix test_app --signal-module test_signals.TestSignals --dry-run
```

#### Step 2.13: Implement Status Command (60 minutes)

```python
# src/champi_ipc/cli/status_cmd.py
import click
from loguru import logger

from champi_ipc.utils.cleanup import list_regions, get_region_info


@click.command()
@click.option(
    '--prefix',
    default='champi_ipc',
    help='Memory region prefix to check'
)
@click.option(
    '--json',
    'output_json',
    is_flag=True,
    help='Output in JSON format'
)
def status(prefix: str, output_json: bool):
    """Show status of shared memory regions.

    Example:
        champi-ipc status --prefix my_app
        champi-ipc status --prefix my_app --json
    """
    import json

    try:
        regions = list_regions(prefix)

        if not regions:
            click.echo(f"No regions found with prefix: {prefix}")
            return

        # Gather info for each region
        region_info = []
        for region_name in regions:
            info = get_region_info(region_name)
            region_info.append(info)

        if output_json:
            click.echo(json.dumps(region_info, indent=2))
        else:
            click.echo(f"\n📊 Shared Memory Regions (prefix: {prefix})\n")
            click.echo(f"{'Region Name':<40} {'Size':<12} {'Status':<12}")
            click.echo("-" * 64)

            for info in region_info:
                name = info['name']
                size = f"{info['size']} bytes" if info['size'] > 0 else "N/A"

                if info['exists'] and info['accessible']:
                    status_icon = "✅ Active"
                elif info['exists']:
                    status_icon = "⚠️  No Access"
                else:
                    status_icon = "❌ Missing"

                click.echo(f"{name:<40} {size:<12} {status_icon}")

            click.echo(f"\nTotal regions: {len(region_info)}")

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
```

Test:
```bash
uv run champi-ipc status --prefix test_app
uv run champi-ipc status --prefix test_app --json
```

#### Step 2.14: Write Unit Tests for Core Classes (120 minutes)

**Test SharedMemoryManager:**

```python
# tests/unit/test_shared_memory.py
import pytest
from enum import IntEnum
from champi_ipc import SharedMemoryManager, StructRegistry

class TestSignals(IntEnum):
    SIGNAL_A = 1
    SIGNAL_B = 2

def pack_signal_a(seq_num, **kwargs):
    return seq_num.to_bytes(8, 'little') + b'\x01' + b'\x00' * 23

def unpack_signal_a(data):
    return {"seq_num": int.from_bytes(data[:8], 'little')}

@pytest.fixture
def registry():
    reg = StructRegistry()
    reg.register(TestSignals.SIGNAL_A, 32, pack_signal_a, unpack_signal_a)
    reg.register(TestSignals.SIGNAL_B, 16, lambda s, **kw: b'\x00' * 16, lambda d: {})
    return reg

@pytest.fixture
def manager(registry):
    mgr = SharedMemoryManager("test_champi", TestSignals, registry)
    mgr.create_regions()
    yield mgr
    mgr.cleanup()

def test_create_regions(manager):
    """Test creating shared memory regions."""
    assert len(manager.memory_regions) == 2
    assert len(manager.ack_regions) == 2
    assert manager.is_creator is True

def test_write_read_signal(manager, registry):
    """Test writing and reading signal data."""
    data = pack_signal_a(42)
    manager.write_signal(TestSignals.SIGNAL_A, data)

    read_data = manager.read_signal(TestSignals.SIGNAL_A)
    assert read_data == data

def test_write_read_ack(manager):
    """Test writing and reading ACK."""
    manager.write_ack(TestSignals.SIGNAL_A, 100)
    ack_seq = manager.read_ack(TestSignals.SIGNAL_A)
    assert ack_seq == 100

def test_attach_regions(registry):
    """Test attaching to existing regions."""
    # Create regions
    creator = SharedMemoryManager("test_attach", TestSignals, registry)
    creator.create_regions()

    try:
        # Attach to them
        consumer = SharedMemoryManager("test_attach", TestSignals, registry)
        consumer.attach_regions()

        assert len(consumer.memory_regions) == 2
        assert consumer.is_creator is False

        consumer.cleanup()
    finally:
        creator.cleanup()
```

Run tests:
```bash
uv run pytest tests/unit/test_shared_memory.py -v
```

**Test SignalProcessor:**

```python
# tests/unit/test_signal_processor.py
import pytest
import time
from blinker import signal

from champi_ipc import SignalProcessor, SharedMemoryManager, StructRegistry

# Use same TestSignals and registry from previous test

@pytest.fixture
def processor(manager):
    proc = SignalProcessor(manager)
    yield proc
    proc.stop()
    proc.disconnect_all()

def test_connect_signal(processor):
    """Test connecting a blinker signal."""
    test_signal = signal('test-signal')

    def mapper(**kwargs):
        return {'text': kwargs.get('text', '')}

    processor.connect_signal(test_signal, TestSignals.SIGNAL_A, mapper)

    assert len(processor.connected_signals) == 1

def test_signal_queuing(processor, manager):
    """Test that signals are queued when emitted."""
    test_signal = signal('queue-test')

    processor.connect_signal(
        test_signal,
        TestSignals.SIGNAL_A,
        lambda text: {'text': text}
    )

    # Emit signal (should be queued)
    test_signal.send(text="Hello")

    # Check queue
    assert processor.queue.size() == 1

def test_signal_processing(processor, manager, registry):
    """Test full signal flow: emit → queue → shared memory."""
    test_signal = signal('process-test')

    processor.connect_signal(
        test_signal,
        TestSignals.SIGNAL_A,
        lambda: {}
    )

    processor.start()

    # Emit signal
    test_signal.send()

    # Wait for processing
    time.sleep(0.5)

    # Check shared memory was written
    data = manager.read_signal(TestSignals.SIGNAL_A)
    assert data[8] == TestSignals.SIGNAL_A  # Check signal type byte

    processor.stop()
```

Run:
```bash
uv run pytest tests/unit/test_signal_processor.py -v
```

**Test SignalReader:**

```python
# tests/unit/test_signal_reader.py
import pytest
from champi_ipc import SignalReader, SharedMemoryManager

def test_register_handler(manager):
    """Test registering a signal handler."""
    reader = SignalReader(manager)

    called = []
    def handler(signal_data):
        called.append(signal_data)

    reader.register_handler(TestSignals.SIGNAL_A, handler)

    assert TestSignals.SIGNAL_A in reader.handlers

def test_poll_once(manager, registry):
    """Test polling for signals."""
    # Write a signal to memory
    data = pack_signal_a(1)
    manager.write_signal(TestSignals.SIGNAL_A, data)

    # Create reader and handler
    reader = SignalReader(manager)
    received = []

    def handler(signal_data):
        received.append(signal_data)

    reader.register_handler(TestSignals.SIGNAL_A, handler)

    # Poll once
    reader.poll_once()

    # Check handler was called
    assert len(received) == 1
    assert received[0].seq_num == 1
```

Run:
```bash
uv run pytest tests/unit/test_signal_reader.py -v
```

#### Step 2.15: Write Integration Test (90 minutes)

```python
# tests/integration/test_full_signal_flow.py
import pytest
import threading
import time
from blinker import signal

from champi_ipc import (
    SharedMemoryManager,
    SignalProcessor,
    SignalReader,
    StructRegistry
)

def test_full_signal_flow(registry):
    """Test complete signal flow: producer → shared memory → consumer."""

    # Create shared memory
    manager_producer = SharedMemoryManager("test_flow", TestSignals, registry)
    manager_producer.create_regions()

    # Create processor
    processor = SignalProcessor(manager_producer)
    test_signal = signal('flow-test')

    processor.connect_signal(
        test_signal,
        TestSignals.SIGNAL_A,
        lambda text: {'text': text}
    )

    processor.start()

    # Create consumer
    manager_consumer = SharedMemoryManager("test_flow", TestSignals, registry)
    manager_consumer.attach_regions()

    reader = SignalReader(manager_consumer)
    received = []

    def handler(signal_data):
        received.append(signal_data.data)

    reader.register_handler(TestSignals.SIGNAL_A, handler)

    # Start reader in thread
    reader_thread = threading.Thread(
        target=lambda: reader.poll_loop(poll_rate_hz=60)
    )
    reader_thread.daemon = True
    reader_thread.start()

    # Emit signals
    test_signal.send(text="Message 1")
    test_signal.send(text="Message 2")
    test_signal.send(text="Message 3")

    # Wait for processing
    time.sleep(1.0)

    # Stop everything
    reader.stop()
    processor.stop()

    # Verify
    assert len(received) == 3

    # Cleanup
    manager_consumer.cleanup()
    manager_producer.cleanup()
```

Run:
```bash
uv run pytest tests/integration/test_full_signal_flow.py -v
```

#### Step 2.16: Add Docstrings to All Methods (60 minutes)

Go through each class and ensure all public methods have comprehensive docstrings with:
- Description
- Args
- Returns
- Raises
- Example

Use the examples from Section 3.2 as templates.

#### Step 2.17: Run Type Checking (30 minutes)

```bash
# Run mypy
uv run mypy src/champi_ipc/

# Fix any type errors
# Common issues:
# - Missing return types
# - Generic type parameters not properly constrained
# - Optional types not handled
```

#### Step 2.18: Run Linting (30 minutes)

```bash
# Run ruff
uv run ruff check src/champi_ipc/

# Auto-fix what's possible
uv run ruff check --fix src/champi_ipc/

# Format with black
uv run black src/champi_ipc/
```

#### Step 2.19: Create Example Scripts (60 minutes)

```python
# examples/basic_usage.py
"""Basic usage example of champi-ipc."""

from enum import IntEnum
import struct
import time
from multiprocessing import Process

from blinker import signal
from champi_ipc import (
    SharedMemoryManager,
    SignalProcessor,
    SignalReader,
    StructRegistry
)

# Define signal types
class MySignals(IntEnum):
    MESSAGE = 1

# Define struct
MESSAGE_STRUCT = struct.Struct("=QB256s")

def pack_message(seq_num: int, text: str) -> bytes:
    text_bytes = text.encode()[:256].ljust(256, b'\x00')
    return MESSAGE_STRUCT.pack(seq_num, MySignals.MESSAGE, text_bytes)

def unpack_message(data: bytes) -> dict:
    seq_num, signal_type, text_bytes = MESSAGE_STRUCT.unpack(data)
    return {
        "seq_num": seq_num,
        "text": text_bytes.rstrip(b'\x00').decode()
    }

# Create registry
registry = StructRegistry()
registry.register(
    MySignals.MESSAGE,
    MESSAGE_STRUCT.size,
    pack_message,
    unpack_message
)

def producer_process():
    """Producer process that emits signals."""
    # Create memory manager
    manager = SharedMemoryManager("example_app", MySignals, registry)
    manager.create_regions()

    # Create processor
    processor = SignalProcessor(manager)

    # Connect signal
    msg_signal = signal('message')
    processor.connect_signal(
        msg_signal,
        MySignals.MESSAGE,
        lambda text: {'text': text}
    )

    processor.start()

    # Emit messages
    for i in range(10):
        msg_signal.send(text=f"Message #{i}")
        time.sleep(0.5)

    # Cleanup
    processor.stop()
    manager.cleanup()

def consumer_process():
    """Consumer process that reads signals."""
    time.sleep(0.5)  # Wait for producer to create regions

    # Attach to regions
    manager = SharedMemoryManager("example_app", MySignals, registry)
    manager.attach_regions()

    # Create reader
    reader = SignalReader(manager)

    # Register handler
    def handle_message(signal_data):
        print(f"[Consumer] Received: {signal_data.data['text']}")

    reader.register_handler(MySignals.MESSAGE, handle_message)

    # Poll for 10 seconds
    import threading
    stop_event = threading.Event()

    def poll():
        while not stop_event.is_set():
            reader.poll_once()
            time.sleep(1.0 / 60)  # 60 Hz

    poll_thread = threading.Thread(target=poll)
    poll_thread.start()

    time.sleep(10)
    stop_event.set()
    poll_thread.join()

    # Cleanup
    manager.cleanup()

if __name__ == "__main__":
    # Start producer
    producer = Process(target=producer_process)
    producer.start()

    # Start consumer
    consumer = Process(target=consumer_process)
    consumer.start()

    # Wait for both
    producer.join()
    consumer.join()

    print("Example complete!")
```

Test example:
```bash
uv run python examples/basic_usage.py
```

#### Step 2.20: Run Full Test Suite (30 minutes)

```bash
# Run all tests with coverage
uv run pytest --cov=src/champi_ipc --cov-report=html --cov-report=term

# Check coverage report
# Target: >90% coverage

# Run on multiple Python versions (if available)
uv run pytest --python 3.12
uv run pytest --python 3.13
```

**Day 3 Checkpoint**: All tests passing, >90% coverage

---

### Phase 3: Library Finalization (Day 4)

**Duration**: 6-8 hours
**Prerequisites**: Phase 2 complete
**Deliverable**: champi-ipc 0.1.0 published to PyPI

#### Step 3.1: Complete API Documentation (120 minutes)

```markdown
# docs/api.md

# champi-ipc API Reference

## Core Classes

### SharedMemoryManager

**Generic shared memory manager for any signal type enum.**

```python
class SharedMemoryManager:
    def __init__(
        self,
        name_prefix: str,
        signal_type_enum: Type[SignalT],
        struct_registry: StructRegistry
    ):
```

**Parameters:**
- `name_prefix` (str): Prefix for shared memory region names. Used to create region names like `{prefix}_{signal_name}`.
- `signal_type_enum` (Type[SignalT]): Enum class defining signal types. Must be an IntEnum.
- `struct_registry` (StructRegistry): Registry mapping signal types to struct operations.

**Methods:**

#### `create_regions()`

Creates shared memory regions for all signal types.

**Raises:**
- `FileExistsError`: If regions already exist
- `PermissionError`: If insufficient permissions

**Example:**
```python
manager = SharedMemoryManager("my_app", MySignals, registry)
manager.create_regions()
```

#### `attach_regions()`

Attaches to existing shared memory regions.

**Raises:**
- `FileNotFoundError`: If regions don't exist

**Example:**
```python
manager = SharedMemoryManager("my_app", MySignals, registry)
manager.attach_regions()  # Consumer process
```

[... continue for all methods ...]

## Base Classes

### StructRegistry

[... full documentation ...]

## Utility Functions

### cleanup_orphaned_regions()

[... full documentation ...]
```

#### Step 3.2: Write Migration Guide (90 minutes)

```markdown
# docs/migration_guide.md

# Migration Guide: Adopting champi-ipc

This guide helps you migrate existing IPC code to use champi-ipc.

## Prerequisites

- Python 3.12+
- Existing signal types defined as IntEnum
- Pack/unpack functions for your signals

## Step 1: Install champi-ipc

```bash
uv pip install champi-ipc==0.1.0
```

## Step 2: Create StructRegistry

**Before (service-specific):**
```python
# structs.py
def get_struct_size(signal_type: SignalType) -> int:
    if signal_type == SignalType.SIGNAL_A:
        return SIGNAL_A_STRUCT.size
    # ... etc

def pack_signal(signal_type: SignalType, seq_num: int, **kwargs) -> bytes:
    if signal_type == SignalType.SIGNAL_A:
        # ... pack logic
    # ... etc
```

**After (using champi-ipc):**
```python
# structs.py
from champi_ipc import StructRegistry

registry = StructRegistry()
registry.register(
    SignalType.SIGNAL_A,
    SIGNAL_A_STRUCT.size,
    pack_signal_a,
    unpack_signal_a
)
```

## Step 3: Update SharedMemoryManager Usage

**Before:**
```python
from my_app.ipc import AssistantSharedMemoryManager

manager = AssistantSharedMemoryManager(name_prefix="my_app")
manager.create_regions()
```

**After:**
```python
from champi_ipc import SharedMemoryManager
from my_app.structs import MySignals, registry

manager = SharedMemoryManager(
    name_prefix="my_app",
    signal_type_enum=MySignals,
    struct_registry=registry
)
manager.create_regions()
```

[... continue with all components ...]
```

#### Step 3.3: Write Troubleshooting Guide (60 minutes)

```markdown
# docs/troubleshooting.md

# Troubleshooting champi-ipc

## Common Issues

### FileExistsError when creating regions

**Symptom:**
```
FileExistsError: [Errno 17] File exists: '/dev/shm/my_app_signal_a'
```

**Cause:** Regions from crashed process not cleaned up.

**Solution:**
```bash
# Clean up orphaned regions
champi-ipc cleanup --prefix my_app --signal-module my_app.signals.MySignals

# Or in code:
from champi_ipc import cleanup_orphaned_regions
cleanup_orphaned_regions("my_app", MySignals)
```

### FileNotFoundError when attaching

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: '/dev/shm/my_app_signal_a'
```

**Cause:** Producer hasn't created regions yet.

**Solution:**
- Ensure producer calls `create_regions()` before consumer calls `attach_regions()`
- Add retry logic in consumer

### Signal Loss Warnings

**Symptom:**
```
⚠️ Signal loss for SIGNAL_A: Reader at 10, writing 50 (40 signals skipped)
```

**Cause:** Consumer not keeping up with producer.

**Solutions:**
1. Increase poll rate: `reader.poll_loop(poll_rate_hz=120)`
2. Optimize handler performance
3. Increase queue size: `SignalQueue(maxsize=500)`

[... more issues ...]
```

#### Step 3.4: Run Pre-commit Hooks (15 minutes)

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Fix any issues
# Common: trailing whitespace, missing newlines

# Commit fixes
git add .
git commit -m "chore: fix pre-commit issues"
```

#### Step 3.5: Tag Release (10 minutes)

```bash
# Ensure all tests pass
uv run pytest

# Tag version
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0

# This triggers release workflow which publishes to PyPI
```

#### Step 3.6: Verify PyPI Release (15 minutes)

```bash
# Wait for GitHub Actions to complete
gh run list

# Check release is on PyPI
pip search champi-ipc

# Test installation
pip install champi-ipc==0.1.0
python -c "from champi_ipc import SharedMemoryManager; print('✅ Import successful')"
```

**Phase 3 Complete**: champi-ipc 0.1.0 published!

---

### Phase 4: Migrate champi (Days 5-6)

**Duration**: 12-14 hours
**Prerequisites**: champi-ipc 0.1.0 published
**Deliverable**: champi using champi-ipc library

[Due to length constraints, I'll continue in the next message with Phases 4-6 and remaining sections...]

---

## To Be Continued

This document will continue with:
- Phase 4: Migrate champi (detailed steps)
- Phase 5: Migrate champi-stt (detailed steps)
- Phase 6: Enhanced Features (detailed steps)
- Sections 5-13 (Code Examples, Testing, Migration Checklist, CLI Spec, API Reference, Risks, Metrics, Timeline, Appendices)

**Current Progress**: ~40% complete (40 pages out of ~80)