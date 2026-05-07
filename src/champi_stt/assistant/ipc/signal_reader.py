"""Signal reader for assistant IPC - shared memory consumer."""

import struct
import threading
import time
from collections.abc import Callable
from typing import Any

from loguru import logger

from .shared_memory import AssistantSharedMemoryManager
from .structs import AssistantSignalType, SignalData, unpack_signal

# Type alias for signal handlers
SignalHandler = Callable[[SignalData], None]


class AssistantSignalReader:
    """Reads signals from shared memory and dispatches to handlers."""

    def __init__(self, memory_manager: AssistantSharedMemoryManager) -> None:
        """Initialize signal reader.

        Args:
            memory_manager: Shared memory manager instance
        """
        self.memory_manager = memory_manager
        self.handlers: dict[AssistantSignalType, SignalHandler] = {}
        self._handlers_lock = threading.Lock()
        self.last_seq_nums: dict[AssistantSignalType, int] = {
            st: 0 for st in AssistantSignalType
        }
        self.running = False

    def register_handler(
        self, signal_type: AssistantSignalType, handler: SignalHandler
    ) -> None:
        """Register a handler function for a signal type.

        Args:
            signal_type: Type of signal to handle
            handler: Handler function with signature: handler(signal_data: SignalData) -> None
        """
        with self._handlers_lock:
            self.handlers[signal_type] = handler
        logger.info(f"Registered handler for {signal_type.name}")

    def poll_once(self) -> None:
        """Poll all signal regions once and dispatch any new signals."""
        for signal_type in AssistantSignalType:
            try:
                # Read from shared memory
                try:
                    raw_data = self.memory_manager.read_signal(signal_type)
                except ValueError as e:
                    logger.debug(f"No memory region for {signal_type.name}: {e}")
                    continue

                # Check if memory is uninitialized (signal_type byte at position 8 is 0)
                if len(raw_data) < 9 or raw_data[8] == 0:
                    continue  # Skip uninitialized memory

                # Unpack struct
                try:
                    signal_data = unpack_signal(raw_data)
                except (ValueError, struct.error) as e:
                    logger.error(
                        f"Failed to unpack signal {signal_type.name}: {e}. "
                        f"Data length: {len(raw_data)} bytes"
                    )
                    continue

                # Check if this is a new signal (sequence number changed)
                if signal_data.seq_num > self.last_seq_nums[signal_type]:
                    # Detect signal loss
                    expected_seq = self.last_seq_nums[signal_type] + 1
                    if signal_data.seq_num > expected_seq:
                        missed = signal_data.seq_num - expected_seq
                        logger.warning(
                            f"⚠️  Signal loss detected for {signal_type.name}: "
                            f"expected seq {expected_seq}, got {signal_data.seq_num} "
                            f"({missed} signals missed)"
                        )

                    self.last_seq_nums[signal_type] = signal_data.seq_num

                    # Dispatch to handler if registered (copy ref under lock)
                    with self._handlers_lock:
                        handler = self.handlers.get(signal_type)
                    if handler is not None:
                        try:
                            handler(signal_data)
                            logger.debug(
                                f"Dispatched {signal_type.name} (seq: {signal_data.seq_num})"
                            )
                        except Exception as e:
                            logger.error(
                                f"Handler error for {signal_type.name} (seq: {signal_data.seq_num}): {e}",
                                exc_info=True,
                            )
                            # Continue processing despite handler error

                    # Write ACK after successfully processing signal
                    try:
                        self.memory_manager.write_ack(signal_type, signal_data.seq_num)
                        logger.debug(
                            f"ACKed {signal_type.name} (seq: {signal_data.seq_num})"
                        )
                    except ValueError as e:
                        logger.error(f"Failed to write ACK for {signal_type.name}: {e}")

            except Exception as e:
                logger.error(
                    f"Unexpected error reading signal {signal_type.name}: {e}",
                    exc_info=True,
                )

    def poll_loop(self, poll_rate_hz: int = 60) -> None:
        """Continuously poll for new signals.

        Args:
            poll_rate_hz: Polling frequency in Hz (default 60)
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

    def stop(self) -> None:
        """Stop the poll loop."""
        self.running = False

    def __enter__(self) -> "AssistantSignalReader":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()
