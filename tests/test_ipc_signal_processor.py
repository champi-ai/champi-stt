"""Tests for IPC signal processor."""

import time

from blinker import Signal

from champi_stt.assistant.ipc import (
    AssistantSharedMemoryManager,
    AssistantSignalProcessor,
    AssistantSignalType,
)
from champi_stt.assistant.ipc.structs import unpack_state_change, unpack_wake_detected


class TestSignalProcessor:
    """Tests for AssistantSignalProcessor."""

    def test_processor_initialization(self):
        """Test processor initialization."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_proc")
        processor = AssistantSignalProcessor(mgr)

        assert processor.memory_manager == mgr
        assert processor.queue.maxsize == 100
        assert not processor.running
        assert processor.processor_thread is None

    def test_connect_signal(self):
        """Test connecting blinker signal."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_connect")
        processor = AssistantSignalProcessor(mgr)

        test_signal = Signal()

        # Connect signal
        processor.connect_signal(
            test_signal,
            AssistantSignalType.WAKE_DETECTED,
            data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")},
        )

        assert len(processor.connected_signals) == 1

    def test_signal_to_queue(self):
        """Test signal emission adds to queue."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_queue")
        processor = AssistantSignalProcessor(mgr)

        test_signal = Signal()
        processor.connect_signal(
            test_signal,
            AssistantSignalType.WAKE_DETECTED,
            data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")},
        )

        # Emit signal
        test_signal.send(wake_word="hey_jarvis")

        # Check queue
        assert processor.queue.size() == 1

        # Get from queue
        signal_type, _seq_num, data = processor.queue.get()
        assert signal_type == AssistantSignalType.WAKE_DETECTED
        assert data["wake_word"] == "hey_jarvis"

    def test_data_mapper_filters_none(self):
        """Test that data mapper returning None skips signal."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_filter")
        processor = AssistantSignalProcessor(mgr)

        test_signal = Signal()
        processor.connect_signal(
            test_signal,
            AssistantSignalType.WAKE_DETECTED,
            data_mapper=lambda **kw: None,  # Always return None
        )

        # Emit signal
        test_signal.send(wake_word="test")

        # Queue should be empty
        assert processor.queue.size() == 0

    def test_processor_start_stop(self):
        """Test starting and stopping processor."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_startstop")
        processor = AssistantSignalProcessor(mgr)

        processor.start()
        assert processor.running
        assert processor.processor_thread is not None
        assert processor.processor_thread.is_alive()

        processor.stop()
        assert not processor.running

        # Wait for thread to finish
        processor.processor_thread.join(timeout=1)
        assert not processor.processor_thread.is_alive()

    def test_full_signal_flow(self):
        """Test complete signal flow from blinker to shared memory."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_flow")

        try:
            mgr.create_regions()
            processor = AssistantSignalProcessor(mgr)

            # Connect signal
            test_signal = Signal()
            processor.connect_signal(
                test_signal,
                AssistantSignalType.WAKE_DETECTED,
                data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")},
            )

            # Start processor
            processor.start()

            # Emit signal
            test_signal.send(wake_word="alexa")

            # Give processor time to process
            time.sleep(0.1)

            # Read from shared memory
            data = mgr.read_signal(AssistantSignalType.WAKE_DETECTED)
            unpacked = unpack_wake_detected(data)

            assert unpacked["wake_word"] == "alexa"

            processor.stop()

        finally:
            mgr.cleanup()

    def test_multiple_signals(self):
        """Test handling multiple signal types."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_multi")

        try:
            mgr.create_regions()
            processor = AssistantSignalProcessor(mgr)

            # Connect multiple signals
            wake_signal = Signal()
            state_signal = Signal()

            processor.connect_signal(
                wake_signal,
                AssistantSignalType.WAKE_DETECTED,
                data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")},
            )

            processor.connect_signal(
                state_signal,
                AssistantSignalType.STATE_CHANGE,
                data_mapper=lambda **kw: {"state": kw.get("state", "")},
            )

            processor.start()

            # Emit both signals
            wake_signal.send(wake_word="jarvis")
            state_signal.send(state="recording")

            # Give processor time
            time.sleep(0.1)

            # Read both
            wake_data = unpack_wake_detected(
                mgr.read_signal(AssistantSignalType.WAKE_DETECTED)
            )
            state_data = unpack_state_change(
                mgr.read_signal(AssistantSignalType.STATE_CHANGE)
            )

            assert wake_data["wake_word"] == "jarvis"
            assert state_data["state"] == "recording"

            processor.stop()

        finally:
            mgr.cleanup()

    def test_queue_overflow(self):
        """Test queue behavior when full."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_overflow")
        processor = AssistantSignalProcessor(mgr)

        test_signal = Signal()
        processor.connect_signal(
            test_signal,
            AssistantSignalType.WAKE_DETECTED,
            data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")},
        )

        # Fill queue beyond capacity
        for i in range(105):  # Max is 100
            test_signal.send(wake_word=f"word_{i}")

        # Queue should drop oldest items
        assert processor.queue.size() <= 100

    def test_ack_tracking(self):
        """Test ACK sequence number tracking."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_ack_proc")

        try:
            mgr.create_regions()
            processor = AssistantSignalProcessor(mgr)

            test_signal = Signal()
            processor.connect_signal(
                test_signal,
                AssistantSignalType.WAKE_DETECTED,
                data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")},
            )

            processor.start()

            # Emit signal
            test_signal.send(wake_word="test")

            time.sleep(0.1)

            # Check ACK was written
            ack_seq = mgr.read_ack(AssistantSignalType.WAKE_DETECTED)
            assert ack_seq > 0

            processor.stop()

        finally:
            mgr.cleanup()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_no_data_mapper(self):
        """Test connecting signal without data mapper."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_nomapper")
        processor = AssistantSignalProcessor(mgr)

        test_signal = Signal()
        processor.connect_signal(
            test_signal, AssistantSignalType.WAKE_DETECTED, data_mapper=None
        )

        # Should use raw kwargs
        test_signal.send(wake_word="test", other="data")

        _signal_type, _seq_num, data = processor.queue.get()
        assert data["wake_word"] == "test"
        assert data["other"] == "data"

    def test_disconnect_on_cleanup(self):
        """Test signals are disconnected on cleanup."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_disconnect")
        processor = AssistantSignalProcessor(mgr)

        test_signal = Signal()
        processor.connect_signal(
            test_signal,
            AssistantSignalType.WAKE_DETECTED,
            data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")},
        )

        # Start and stop
        processor.start()
        processor.stop()

        # Signals should still be connected (processor doesn't auto-disconnect)
        assert len(processor.connected_signals) == 1

    def test_restart_processor(self):
        """Test restarting processor."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_restart")
        processor = AssistantSignalProcessor(mgr)

        # First start
        processor.start()
        assert processor.running

        # Try to start again (should warn)
        processor.start()  # Should log warning but not crash

        processor.stop()
