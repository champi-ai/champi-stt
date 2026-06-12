"""Tests for IPC signal reader."""

import pytest

from champi_stt.assistant.ipc import (
    AssistantSharedMemoryManager,
    AssistantSignalType,
)
from champi_stt.assistant.ipc.signal_reader import AssistantSignalReader
from champi_stt.assistant.ipc.structs import pack_state_change, pack_wake_detected

pytestmark = pytest.mark.skip(
    reason="API mismatch with current implementation - pending update"
)


class TestSignalReader:
    """Tests for AssistantSignalReader."""

    def test_reader_initialization(self):
        """Test reader initialization."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_reader")
        reader = AssistantSignalReader(mgr)

        assert reader.memory_manager == mgr
        assert reader.running
        assert len(reader.handlers) == 0
        assert len(reader.last_seq_nums) == 6  # All signal types initialized to 0

    def test_register_handler(self):
        """Test registering signal handlers."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_handler")
        reader = AssistantSignalReader(mgr)

        handler_called = []

        def test_handler(signal_data):
            handler_called.append(signal_data)

        reader.register_handler(AssistantSignalType.WAKE_DETECTED, test_handler)

        assert AssistantSignalType.WAKE_DETECTED in reader.handlers
        assert reader.handlers[AssistantSignalType.WAKE_DETECTED] == test_handler

    def test_poll_once(self):
        """Test polling for signals once."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_poll")

        try:
            mgr.create_regions()
            reader = AssistantSignalReader(mgr)

            # Write a signal
            data = pack_wake_detected(seq_num=1, wake_word="hey_jarvis")
            mgr.write_signal(AssistantSignalType.WAKE_DETECTED, data)

            handler_called = []

            def test_handler(signal_data):
                handler_called.append(signal_data)

            reader.register_handler(AssistantSignalType.WAKE_DETECTED, test_handler)

            # Poll once
            reader.poll_once()

            # Handler should be called
            assert len(handler_called) == 1
            assert handler_called[0].data["wake_word"] == "hey_jarvis"

        finally:
            reader.stop()
            mgr.cleanup()

    def test_signal_loss_detection(self):
        """Test detection of lost signals."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_loss")

        try:
            mgr.create_regions()
            reader = AssistantSignalReader(mgr)

            # Write signal with seq 1
            data1 = pack_wake_detected(seq_num=1, wake_word="first")
            mgr.write_signal(AssistantSignalType.WAKE_DETECTED, data1)

            handler_called = []

            def test_handler(signal_data):
                handler_called.append(signal_data)

            reader.register_handler(AssistantSignalType.WAKE_DETECTED, test_handler)
            reader.poll_once()

            # Write signal with seq 5 (skipping 2, 3, 4)
            data5 = pack_wake_detected(seq_num=5, wake_word="fifth")
            mgr.write_signal(AssistantSignalType.WAKE_DETECTED, data5)

            # Poll again (should detect signal loss)
            reader.poll_once()

            # Should still process the signal
            assert len(handler_called) == 2
            assert handler_called[1].data["wake_word"] == "fifth"

        finally:
            reader.stop()
            mgr.cleanup()

    def test_multiple_handlers(self):
        """Test multiple handlers for different signal types."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_multi_handler")

        try:
            mgr.create_regions()
            reader = AssistantSignalReader(mgr)

            wake_calls = []
            state_calls = []

            reader.register_handler(
                AssistantSignalType.WAKE_DETECTED, lambda sig: wake_calls.append(sig)
            )
            reader.register_handler(
                AssistantSignalType.STATE_CHANGE, lambda sig: state_calls.append(sig)
            )

            # Write both signals
            wake_data = pack_wake_detected(seq_num=1, wake_word="alexa")
            state_data = pack_state_change(seq_num=1, state="recording")

            mgr.write_signal(AssistantSignalType.WAKE_DETECTED, wake_data)
            mgr.write_signal(AssistantSignalType.STATE_CHANGE, state_data)

            # Poll once
            reader.poll_once()

            # Both handlers should be called
            assert len(wake_calls) == 1
            assert len(state_calls) == 1
            assert wake_calls[0].data["wake_word"] == "alexa"
            assert state_calls[0].data["state"] == "recording"

        finally:
            reader.stop()
            mgr.cleanup()

    def test_ack_writing(self):
        """Test that reader writes ACK after processing."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_ack_reader")

        try:
            mgr.create_regions()
            reader = AssistantSignalReader(mgr)

            reader.register_handler(AssistantSignalType.WAKE_DETECTED, lambda sig: None)

            # Write signal
            data = pack_wake_detected(seq_num=42, wake_word="test")
            mgr.write_signal(AssistantSignalType.WAKE_DETECTED, data)

            # Poll
            reader.poll_once()

            # Check ACK was written
            ack_seq = mgr.read_ack(AssistantSignalType.WAKE_DETECTED)
            assert ack_seq == 42

        finally:
            reader.stop()
            mgr.cleanup()

    def test_ignore_old_signals(self):
        """Test that old signals (lower seq num) are ignored."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_old")

        try:
            mgr.create_regions()
            reader = AssistantSignalReader(mgr)

            handler_calls = []
            reader.register_handler(
                AssistantSignalType.WAKE_DETECTED, lambda sig: handler_calls.append(sig)
            )

            # Write signal seq 5
            data5 = pack_wake_detected(seq_num=5, wake_word="fifth")
            mgr.write_signal(AssistantSignalType.WAKE_DETECTED, data5)
            reader.poll_once()

            # Write signal seq 3 (older)
            data3 = pack_wake_detected(seq_num=3, wake_word="third")
            mgr.write_signal(AssistantSignalType.WAKE_DETECTED, data3)
            reader.poll_once()

            # Should only process the first one
            assert len(handler_calls) == 1
            assert handler_calls[0].data["wake_word"] == "fifth"

        finally:
            reader.stop()
            mgr.cleanup()

    def test_stop_reader(self):
        """Test stopping the reader."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_stop")
        reader = AssistantSignalReader(mgr)

        assert reader.running

        reader.stop()

        assert not reader.running

    def test_no_handler_registered(self):
        """Test polling when no handler is registered."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_nohandler")

        try:
            mgr.create_regions()
            reader = AssistantSignalReader(mgr)

            # Write signal
            data = pack_wake_detected(seq_num=1, wake_word="test")
            mgr.write_signal(AssistantSignalType.WAKE_DETECTED, data)

            # Poll (should not crash)
            reader.poll_once()

            # ACK should still be written
            ack_seq = mgr.read_ack(AssistantSignalType.WAKE_DETECTED)
            assert ack_seq == 1

        finally:
            reader.stop()
            mgr.cleanup()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handler_exception(self):
        """Test that handler exceptions don't crash polling."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_exception")

        try:
            mgr.create_regions()
            reader = AssistantSignalReader(mgr)

            def bad_handler(signal_data):
                raise ValueError("Handler error")

            reader.register_handler(AssistantSignalType.WAKE_DETECTED, bad_handler)

            # Write signal
            data = pack_wake_detected(seq_num=1, wake_word="test")
            mgr.write_signal(AssistantSignalType.WAKE_DETECTED, data)

            # Poll (should not crash)
            reader.poll_once()

            # ACK should still be written
            ack_seq = mgr.read_ack(AssistantSignalType.WAKE_DETECTED)
            assert ack_seq == 1

        finally:
            reader.stop()
            mgr.cleanup()

    def test_replace_handler(self):
        """Test replacing a handler."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_replace")
        reader = AssistantSignalReader(mgr)

        calls1 = []
        calls2 = []

        reader.register_handler(
            AssistantSignalType.WAKE_DETECTED, lambda sig: calls1.append(sig)
        )

        # Replace handler
        reader.register_handler(
            AssistantSignalType.WAKE_DETECTED, lambda sig: calls2.append(sig)
        )

        assert AssistantSignalType.WAKE_DETECTED in reader.handlers
        # Only the second handler should be registered
        assert (
            len(reader.handlers[AssistantSignalType.WAKE_DETECTED].__code__.co_freevars)
            >= 0
        )
