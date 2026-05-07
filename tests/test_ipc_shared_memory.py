"""Tests for IPC shared memory manager."""

from multiprocessing import shared_memory

import pytest

from champi_stt.assistant.ipc import (
    AssistantSharedMemoryManager,
    AssistantSignalType,
    cleanup_orphaned_regions,
)
from champi_stt.assistant.ipc.structs import (
    pack_error,
    pack_executing,
    pack_recording,
    pack_state_change,
    pack_transcribing,
    pack_wake_detected,
    unpack_error,
    unpack_executing,
    unpack_recording,
    unpack_state_change,
    unpack_transcribing,
    unpack_wake_detected,
)


class TestSharedMemoryManager:
    """Tests for AssistantSharedMemoryManager."""

    def test_manager_initialization(self):
        """Test manager initialization with custom prefix."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_champi")
        assert mgr.name_prefix == "test_champi"
        assert len(mgr.memory_regions) == 0
        assert len(mgr.ack_regions) == 0
        assert not mgr.is_creator

    def test_create_regions(self):
        """Test creating shared memory regions."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_create")

        try:
            mgr.create_regions()

            assert mgr.is_creator
            assert len(mgr.memory_regions) == 6  # 6 signal types
            assert len(mgr.ack_regions) == 6

            # Check all signal types have regions
            for signal_type in AssistantSignalType:
                assert signal_type in mgr.memory_regions
                assert signal_type in mgr.ack_regions

        finally:
            mgr.cleanup()

    def test_attach_regions(self):
        """Test attaching to existing shared memory regions."""
        creator = AssistantSharedMemoryManager(name_prefix="test_attach")
        consumer = AssistantSharedMemoryManager(name_prefix="test_attach")

        try:
            # Creator creates regions first
            creator.create_regions()

            # Consumer attaches
            consumer.attach_regions()

            assert not consumer.is_creator
            assert len(consumer.memory_regions) == 6
            assert len(consumer.ack_regions) == 6

        finally:
            consumer.cleanup()  # Close only
            creator.cleanup()  # Unlink

    def test_write_and_read_signal(self):
        """Test writing and reading signals."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_rw")

        try:
            mgr.create_regions()

            # Write wake detected signal
            data = pack_wake_detected(seq_num=1, wake_word="hey_jarvis")
            mgr.write_signal(AssistantSignalType.WAKE_DETECTED, data)

            # Read back
            read_data = mgr.read_signal(AssistantSignalType.WAKE_DETECTED)
            unpacked = unpack_wake_detected(read_data)

            assert unpacked["seq_num"] == 1
            assert unpacked["wake_word"] == "hey_jarvis"

        finally:
            mgr.cleanup()

    def test_write_and_read_ack(self):
        """Test writing and reading ACK sequence numbers."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_ack")

        try:
            mgr.create_regions()

            # Write ACK
            mgr.write_ack(AssistantSignalType.STATE_CHANGE, seq_num=42)

            # Read back
            ack_seq = mgr.read_ack(AssistantSignalType.STATE_CHANGE)
            assert ack_seq == 42

        finally:
            mgr.cleanup()

    def test_context_manager(self):
        """Test manager as context manager."""
        with AssistantSharedMemoryManager(name_prefix="test_ctx") as mgr:
            mgr.create_regions()
            assert len(mgr.memory_regions) == 6

        # Should be cleaned up
        assert len(mgr.memory_regions) == 0

    def test_signal_data_integrity(self):
        """Test all signal types for data integrity."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_integrity")

        try:
            mgr.create_regions()

            # Test STATE_CHANGE
            state_data = pack_state_change(seq_num=1, state="recording")
            mgr.write_signal(AssistantSignalType.STATE_CHANGE, state_data)
            unpacked_state = unpack_state_change(
                mgr.read_signal(AssistantSignalType.STATE_CHANGE)
            )
            assert unpacked_state["state"] == "recording"

            # Test RECORDING
            rec_data = pack_recording(seq_num=2, duration=5.5, is_active=True)
            mgr.write_signal(AssistantSignalType.RECORDING, rec_data)
            unpacked_rec = unpack_recording(
                mgr.read_signal(AssistantSignalType.RECORDING)
            )
            assert unpacked_rec["duration"] == pytest.approx(5.5)
            assert unpacked_rec["is_active"] is True

            # Test TRANSCRIBING
            trans_data = pack_transcribing(
                seq_num=3, partial_text="hello world", is_final=False
            )
            mgr.write_signal(AssistantSignalType.TRANSCRIBING, trans_data)
            unpacked_trans = unpack_transcribing(
                mgr.read_signal(AssistantSignalType.TRANSCRIBING)
            )
            assert unpacked_trans["partial_text"] == "hello world"
            assert unpacked_trans["is_final"] is False

            # Test EXECUTING
            exec_data = pack_executing(seq_num=4, command="turn on lights")
            mgr.write_signal(AssistantSignalType.EXECUTING, exec_data)
            unpacked_exec = unpack_executing(
                mgr.read_signal(AssistantSignalType.EXECUTING)
            )
            assert unpacked_exec["command"] == "turn on lights"

            # Test ERROR
            error_data = pack_error(
                seq_num=5, error_message="Connection failed", error_type="network"
            )
            mgr.write_signal(AssistantSignalType.ERROR, error_data)
            unpacked_error = unpack_error(mgr.read_signal(AssistantSignalType.ERROR))
            assert unpacked_error["error_message"] == "Connection failed"
            assert unpacked_error["error_type"] == "network"

        finally:
            mgr.cleanup()


class TestCleanupOrphanedRegions:
    """Tests for cleanup_orphaned_regions utility."""

    def test_cleanup_orphaned_regions(self):
        """Test cleaning up orphaned regions."""
        # Create some orphaned regions
        mgr = AssistantSharedMemoryManager(name_prefix="test_orphan")
        mgr.create_regions()
        # Don't cleanup (simulate crash)

        # Now cleanup orphaned
        cleaned = cleanup_orphaned_regions(name_prefix="test_orphan")

        # Should have cleaned 12 regions (6 data + 6 ACK)
        assert len(cleaned) == 12

        # Verify regions are gone
        for signal_type in AssistantSignalType:
            region_name = f"test_orphan_{signal_type.name.lower()}"
            with pytest.raises(FileNotFoundError):
                shm = shared_memory.SharedMemory(name=region_name)
                shm.close()
                shm.unlink()

            ack_region_name = f"test_orphan_{signal_type.name.lower()}_ack"
            with pytest.raises(FileNotFoundError):
                ack_shm = shared_memory.SharedMemory(name=ack_region_name)
                ack_shm.close()
                ack_shm.unlink()

    def test_cleanup_nonexistent_regions(self):
        """Test cleanup when no regions exist."""
        cleaned = cleanup_orphaned_regions(name_prefix="nonexistent_prefix")
        assert len(cleaned) == 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_write_wrong_size(self):
        """Test writing data with wrong size."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_size")

        try:
            mgr.create_regions()

            # Try to write data with wrong size
            with pytest.raises(ValueError, match="Data size mismatch"):
                mgr.write_signal(AssistantSignalType.WAKE_DETECTED, b"short")

        finally:
            mgr.cleanup()

    def test_attach_before_create(self):
        """Test attaching when regions don't exist."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_noexist")

        with pytest.raises(FileNotFoundError):
            mgr.attach_regions()

    def test_read_uninitialized_signal(self):
        """Test reading from uninitialized manager."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_uninit")

        with pytest.raises(ValueError, match="No memory region"):
            mgr.read_signal(AssistantSignalType.WAKE_DETECTED)

    def test_long_strings_truncated(self):
        """Test that long strings are truncated to fit struct."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_long")

        try:
            mgr.create_regions()

            # Very long wake word (should be truncated)
            long_word = "x" * 1000
            data = pack_wake_detected(seq_num=1, wake_word=long_word)
            mgr.write_signal(AssistantSignalType.WAKE_DETECTED, data)

            unpacked = unpack_wake_detected(
                mgr.read_signal(AssistantSignalType.WAKE_DETECTED)
            )
            # Should be truncated to MAX_WAKE_WORD_SIZE (64 bytes)
            assert len(unpacked["wake_word"]) <= 64

        finally:
            mgr.cleanup()
