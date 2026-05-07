"""Signal processor for assistant IPC - blinker to shared memory bridge."""

import threading
from collections.abc import Callable
from typing import Any

from blinker import Signal
from loguru import logger

from .shared_memory import AssistantSharedMemoryManager
from .signal_queue import SignalQueue
from .structs import AssistantSignalType, pack_signal

# Type alias for data mapper functions
DataMapper = Callable[..., dict[str, Any] | None]


class AssistantSignalProcessor:
    """Bridges blinker signals to shared memory via FIFO queue."""

    def __init__(self, memory_manager: AssistantSharedMemoryManager) -> None:
        """Initialize signal processor.

        Args:
            memory_manager: Shared memory manager instance
        """
        self.memory_manager = memory_manager
        self.queue = SignalQueue(maxsize=100)
        self.running = False
        self.processor_thread: threading.Thread | None = None

        # Track connected signals
        self.connected_signals: list[tuple[Signal, Callable]] = []

    def connect_signal(
        self,
        signal: Signal,
        signal_type: AssistantSignalType,
        data_mapper: DataMapper | None = None,
    ) -> None:
        """Connect a blinker signal to the processor.

        Args:
            signal: Blinker signal to connect
            signal_type: AssistantSignalType enum value
            data_mapper: Optional function to map signal kwargs to queue data
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
                f"Queued signal {signal_type.name} (seq: {seq_num}, queue size: {self.queue.size()})"
            )

        signal.connect(signal_handler, weak=False)
        self.connected_signals.append((signal, signal_handler))

        logger.info(f"Connected signal processor for {signal_type.name}")

    def start(self) -> None:
        """Start processing signals from queue."""
        if self.running:
            logger.warning("Signal processor already running")
            return

        self.running = True
        self.processor_thread = threading.Thread(
            target=self._process_loop, daemon=True, name="AssistantSignalProcessor"
        )
        self.processor_thread.start()

        logger.info("Assistant signal processor started")

    def stop(self) -> None:
        """Stop processing signals."""
        self.running = False

        if self.processor_thread:
            self.processor_thread.join(timeout=2.0)
            self.processor_thread = None

        logger.info("Assistant signal processor stopped")

    def _process_loop(self) -> None:
        """Main processing loop - pulls from queue and writes to shared memory."""
        consecutive_errors = 0
        max_consecutive_errors = 10

        while self.running:
            # Get next item from queue (blocks with timeout)
            try:
                item = self.queue.get(timeout=0.5)

                if item is None:
                    continue  # Timeout, check if still running

                # Reset error counter on successful get
                consecutive_errors = 0

            except Exception as e:
                logger.error(f"Error getting item from queue: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(
                        f"Too many consecutive queue errors ({consecutive_errors}), stopping processor"
                    )
                    self.running = False
                continue

            try:
                # Check ACK to detect missed signals
                try:
                    ack_seq = self.memory_manager.read_ack(item.signal_type)
                except ValueError as e:
                    logger.error(f"Failed to read ACK for {item.signal_type.name}: {e}")
                    ack_seq = 0  # Assume no ACK

                expected_ack = (
                    item.seq_num - 1
                )  # Reader should have ACKed previous signal

                if ack_seq < expected_ack:
                    # Reader hasn't processed previous signal yet - potential signal loss
                    missed_count = expected_ack - ack_seq
                    # Only warn if significant signal loss (>3 signals)
                    if missed_count > 3:
                        logger.warning(
                            f"⚠️  Potential signal loss for {item.signal_type.name}: "
                            f"Reader at seq {ack_seq}, writing seq {item.seq_num} "
                            f"({missed_count} signals may be skipped)"
                        )
                    else:
                        logger.debug(
                            f"Reader slightly behind for {item.signal_type.name}: "
                            f"{missed_count} signals pending"
                        )

                # Pack signal data into binary struct
                try:
                    packed_data = pack_signal(
                        item.signal_type, item.seq_num, **item.data
                    )
                except (ValueError, KeyError, TypeError) as e:
                    logger.error(
                        f"Failed to pack signal {item.signal_type.name} (seq: {item.seq_num}): {e}. "
                        f"Data: {item.data}"
                    )
                    continue

                # Write to appropriate shared memory region
                try:
                    self.memory_manager.write_signal(item.signal_type, packed_data)
                    logger.debug(
                        f"Wrote {item.signal_type.name} to shared memory (seq: {item.seq_num})"
                    )
                except ValueError as e:
                    logger.error(
                        f"Failed to write signal {item.signal_type.name} to shared memory: {e}"
                    )
                    continue

            except Exception as e:
                logger.error(
                    f"Unexpected error processing signal {item.signal_type.name}: {e}",
                    exc_info=True,
                )
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(
                        f"Too many consecutive processing errors ({consecutive_errors}), stopping processor"
                    )
                    self.running = False

    def disconnect_all(self) -> None:
        """Disconnect all signal handlers."""
        for signal, handler in self.connected_signals:
            signal.disconnect(handler)

        self.connected_signals.clear()
        logger.info("Disconnected all signal handlers")

    def __enter__(self) -> "AssistantSignalProcessor":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()
        self.disconnect_all()
