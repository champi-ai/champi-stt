"""Integration tests for IPC system - end-to-end signal flow."""

import time

import pytest
from blinker import Signal

from champi_stt.assistant.ipc import (
    AssistantSharedMemoryManager,
    AssistantSignalManager,
    AssistantSignalProcessor,
    AssistantSignalType,
)
from champi_stt.assistant.ipc.signal_reader import AssistantSignalReader


class TestEndToEndSignalFlow:
    """Integration tests for complete signal flow."""

    def test_full_ipc_pipeline(self):
        """Test complete pipeline: blinker → processor → shared memory → reader."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_e2e")

        try:
            mgr.create_regions()

            # Setup processor
            processor = AssistantSignalProcessor(mgr)
            test_signal = Signal()

            processor.connect_signal(
                test_signal,
                AssistantSignalType.WAKE_DETECTED,
                data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")}
            )

            processor.start()

            # Setup reader
            reader = AssistantSignalReader(mgr)
            received_signals = []

            reader.register_handler(
                AssistantSignalType.WAKE_DETECTED,
                lambda sig: received_signals.append(sig)
            )

            # Emit signal
            test_signal.send(wake_word="hey_jarvis")

            # Give time to process
            time.sleep(0.2)

            # Poll reader
            reader.poll_once()

            # Verify signal was received
            assert len(received_signals) == 1
            assert received_signals[0].data["wake_word"] == "hey_jarvis"

            processor.stop()
            reader.stop()

        finally:
            mgr.cleanup()

    def test_multiple_signal_types_flow(self):
        """Test flow with multiple signal types."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_multi_e2e")

        try:
            mgr.create_regions()

            # Setup processor with multiple signals
            processor = AssistantSignalProcessor(mgr)
            wake_signal = Signal()
            state_signal = Signal()
            error_signal = Signal()

            processor.connect_signal(
                wake_signal,
                AssistantSignalType.WAKE_DETECTED,
                data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")}
            )

            processor.connect_signal(
                state_signal,
                AssistantSignalType.STATE_CHANGE,
                data_mapper=lambda **kw: {"state": kw.get("state", "")}
            )

            processor.connect_signal(
                error_signal,
                AssistantSignalType.ERROR,
                data_mapper=lambda **kw: {
                    "error_message": kw.get("error_message", ""),
                    "error_type": kw.get("error_type", "")
                }
            )

            processor.start()

            # Setup reader
            reader = AssistantSignalReader(mgr)
            wake_calls = []
            state_calls = []
            error_calls = []

            reader.register_handler(AssistantSignalType.WAKE_DETECTED, lambda sig: wake_calls.append(sig))
            reader.register_handler(AssistantSignalType.STATE_CHANGE, lambda sig: state_calls.append(sig))
            reader.register_handler(AssistantSignalType.ERROR, lambda sig: error_calls.append(sig))

            # Emit multiple signals
            wake_signal.send(wake_word="alexa")
            state_signal.send(state="recording")
            error_signal.send(error_message="Test error", error_type="test")

            time.sleep(0.2)
            reader.poll_once()

            # Verify all received
            assert len(wake_calls) == 1
            assert len(state_calls) == 1
            assert len(error_calls) == 1

            processor.stop()
            reader.stop()

        finally:
            mgr.cleanup()

    def test_signal_manager_integration(self):
        """Test integration with AssistantSignalManager."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_sig_mgr")

        try:
            mgr.create_regions()

            # Get signal manager
            signal_mgr = AssistantSignalManager()

            # Setup processor
            processor = AssistantSignalProcessor(mgr)

            processor.connect_signal(
                signal_mgr.processing,
                AssistantSignalType.WAKE_DETECTED,
                data_mapper=lambda **kw: {"wake_word": kw.get("data", {}).get("wake_word", "")}
                if kw.get("sub_event") == "WAKE_DETECTED" else None
            )

            processor.start()

            # Setup reader
            reader = AssistantSignalReader(mgr)
            received = []

            reader.register_handler(AssistantSignalType.WAKE_DETECTED, lambda sig: received.append(sig))

            # Emit via signal manager
            signal_mgr.processing.send(
                event_type="processing",
                sub_event="WAKE_DETECTED",
                data={"wake_word": "computer"}
            )

            time.sleep(0.2)
            reader.poll_once()

            # Verify
            assert len(received) == 1
            assert received[0].data["wake_word"] == "computer"

            processor.stop()
            reader.stop()

        finally:
            mgr.cleanup()

    def test_high_frequency_signals(self):
        """Test handling high-frequency signal emission."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_hf")

        try:
            mgr.create_regions()

            processor = AssistantSignalProcessor(mgr)
            test_signal = Signal()

            processor.connect_signal(
                test_signal,
                AssistantSignalType.WAKE_DETECTED,
                data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")}
            )

            processor.start()

            # Emit 50 signals rapidly
            for i in range(50):
                test_signal.send(wake_word=f"word_{i}")

            time.sleep(0.5)  # Give time to process

            # Setup reader
            reader = AssistantSignalReader(mgr)
            received = []
            reader.register_handler(AssistantSignalType.WAKE_DETECTED, lambda sig: received.append(sig))

            reader.poll_once()

            # Should have received the last signal
            assert len(received) >= 1

            processor.stop()
            reader.stop()

        finally:
            mgr.cleanup()

    def test_concurrent_readers(self):
        """Test multiple readers reading same signals."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_concurrent")

        try:
            mgr.create_regions()

            # Setup processor
            processor = AssistantSignalProcessor(mgr)
            test_signal = Signal()

            processor.connect_signal(
                test_signal,
                AssistantSignalType.WAKE_DETECTED,
                data_mapper=lambda **kw: {"wake_word": kw.get("wake_word", "")}
            )

            processor.start()

            # Setup two readers
            reader1 = AssistantSignalReader(mgr)
            reader2 = AssistantSignalReader(mgr)

            received1 = []
            received2 = []

            reader1.register_handler(AssistantSignalType.WAKE_DETECTED, lambda sig: received1.append(sig))
            reader2.register_handler(AssistantSignalType.WAKE_DETECTED, lambda sig: received2.append(sig))

            # Emit signal
            test_signal.send(wake_word="shared")

            time.sleep(0.2)

            reader1.poll_once()
            reader2.poll_once()

            # Both should receive
            assert len(received1) == 1
            assert len(received2) == 1
            assert received1[0].data["wake_word"] == "shared"
            assert received2[0].data["wake_word"] == "shared"

            processor.stop()
            reader1.stop()
            reader2.stop()

        finally:
            mgr.cleanup()


@pytest.mark.integration
class TestRealWorldScenarios:
    """Integration tests simulating real-world usage."""

    def test_assistant_workflow_simulation(self):
        """Simulate a complete assistant workflow."""
        mgr = AssistantSharedMemoryManager(name_prefix="test_workflow")

        try:
            mgr.create_regions()

            signal_mgr = AssistantSignalManager()
            processor = AssistantSignalProcessor(mgr)

            # Connect all signal types as in daemon
            processor.connect_signal(
                signal_mgr.state,
                AssistantSignalType.STATE_CHANGE,
                data_mapper=lambda **kw: {"state": kw.get("sub_event", "").lower()}
            )

            processor.connect_signal(
                signal_mgr.processing,
                AssistantSignalType.WAKE_DETECTED,
                data_mapper=lambda **kw: {"wake_word": kw.get("data", {}).get("wake_word", "")}
                if kw.get("sub_event") == "WAKE_DETECTED" else None
            )

            processor.start()

            # Setup reader
            reader = AssistantSignalReader(mgr)
            state_changes = []
            wake_detections = []

            reader.register_handler(AssistantSignalType.STATE_CHANGE, lambda sig: state_changes.append(sig))
            reader.register_handler(AssistantSignalType.WAKE_DETECTED, lambda sig: wake_detections.append(sig))

            # Simulate workflow
            signal_mgr.state.send(event_type="state", sub_event="LISTENING_START")
            time.sleep(0.1)
            reader.poll_once()

            signal_mgr.processing.send(
                event_type="processing",
                sub_event="WAKE_DETECTED",
                data={"wake_word": "hey_jarvis"}
            )
            time.sleep(0.1)
            reader.poll_once()

            signal_mgr.state.send(event_type="state", sub_event="RECORDING_START")
            time.sleep(0.1)
            reader.poll_once()

            # Verify workflow
            assert len(state_changes) >= 2
            assert len(wake_detections) == 1
            assert "listening" in state_changes[0].data["state"]
            assert wake_detections[0].data["wake_word"] == "hey_jarvis"

            processor.stop()
            reader.stop()

        finally:
            mgr.cleanup()
