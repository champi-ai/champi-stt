"""FIFO signal queue for assistant IPC."""

import threading
from collections import deque
from typing import Optional

from .structs import AssistantSignalType


class SignalQueueItem:
    """Item in the signal queue."""

    def __init__(self, signal_type: AssistantSignalType, seq_num: int, **kwargs):
        """Initialize queue item.

        Args:
            signal_type: Type of signal
            seq_num: Sequence number
            **kwargs: Signal data
        """
        self.signal_type = signal_type
        self.seq_num = seq_num
        self.data = kwargs


class SignalQueue:
    """Thread-safe FIFO queue for assistant signals."""

    def __init__(self, maxsize: int = 100):
        """Initialize signal queue.

        Args:
            maxsize: Maximum queue size
        """
        self.maxsize = maxsize
        self._queue = deque(maxlen=maxsize)
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._sequence_counter = 0

    def put(self, signal_type: AssistantSignalType, **kwargs) -> int:
        """Add signal to queue.

        Args:
            signal_type: Type of signal
            **kwargs: Signal data

        Returns:
            Sequence number
        """
        with self._lock:
            self._sequence_counter += 1
            seq_num = self._sequence_counter

            item = SignalQueueItem(signal_type, seq_num, **kwargs)
            self._queue.append(item)

            self._not_empty.notify()

            return seq_num

    def get(self, timeout: Optional[float] = None) -> Optional[SignalQueueItem]:
        """Get next signal from queue (blocks if empty).

        Args:
            timeout: Timeout in seconds

        Returns:
            Signal queue item or None on timeout
        """
        with self._not_empty:
            while len(self._queue) == 0:
                if not self._not_empty.wait(timeout=timeout):
                    return None  # Timeout

            return self._queue.popleft()

    def get_nowait(self) -> Optional[SignalQueueItem]:
        """Get next signal without blocking.

        Returns:
            Signal queue item or None if empty
        """
        with self._lock:
            if len(self._queue) == 0:
                return None
            return self._queue.popleft()

    def size(self) -> int:
        """Get current queue size.

        Returns:
            Number of items in queue
        """
        with self._lock:
            return len(self._queue)

    def clear(self):
        """Clear all items from queue."""
        with self._lock:
            self._queue.clear()
