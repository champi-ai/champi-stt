"""Binary struct definitions for assistant IPC signals."""

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict

# Maximum sizes for string fields
MAX_STATE_SIZE = 32
MAX_TEXT_SIZE = 256
MAX_ERROR_SIZE = 512

# Padding character for string fields
PAD_CHAR = "#"


class AssistantSignalType(IntEnum):
    """Signal type identifiers for assistant events."""

    STATE_CHANGE = 1
    WAKE_DETECTED = 2
    RECORDING = 3
    TRANSCRIBING = 4
    EXECUTING = 5
    ERROR = 6


# Binary struct formats for each signal type
STATE_CHANGE_STRUCT = struct.Struct(f"=QB{MAX_STATE_SIZE}s")
WAKE_DETECTED_STRUCT = struct.Struct(f"=QB{MAX_TEXT_SIZE}s")
RECORDING_STRUCT = struct.Struct("=QBd?")  # seq, signal_type, duration, is_active
TRANSCRIBING_STRUCT = struct.Struct(
    f"=QB{MAX_TEXT_SIZE}s?"
)  # seq, signal_type, partial_text, is_final
EXECUTING_STRUCT = struct.Struct(
    f"=QB{MAX_TEXT_SIZE}s"
)  # seq, signal_type, command
ERROR_STRUCT = struct.Struct(
    f"=QB{MAX_ERROR_SIZE}s{MAX_TEXT_SIZE}s"
)  # seq, signal_type, error_message, error_type

# ACK struct: seq_num(Q) - sequence number the reader processed
ACK_STRUCT = struct.Struct("=Q")


@dataclass
class SignalData:
    """Container for unpacked signal data."""

    signal_type: AssistantSignalType
    seq_num: int
    data: Dict[str, Any]


def _pad_string(s: str, size: int) -> bytes:
    """Pad string to fixed size with PAD_CHAR."""
    s_bytes = s.encode("utf-8")[:size]
    return s_bytes + (PAD_CHAR.encode() * (size - len(s_bytes)))


def _unpad_string(b: bytes) -> str:
    """Remove padding from string."""
    return b.rstrip(PAD_CHAR.encode()).decode("utf-8", errors="ignore")


def pack_signal(signal_type: AssistantSignalType, seq_num: int, **kwargs) -> bytes:
    """Pack signal data into binary struct.

    Args:
        signal_type: Type of signal to pack
        seq_num: Sequence number for signal tracking
        **kwargs: Signal-specific data fields

    Returns:
        Packed binary data
    """
    if signal_type == AssistantSignalType.STATE_CHANGE:
        state = kwargs.get("state", "")
        return STATE_CHANGE_STRUCT.pack(
            seq_num, signal_type.value, _pad_string(state, MAX_STATE_SIZE)
        )

    elif signal_type == AssistantSignalType.WAKE_DETECTED:
        wake_word = kwargs.get("wake_word", "")
        return WAKE_DETECTED_STRUCT.pack(
            seq_num, signal_type.value, _pad_string(wake_word, MAX_TEXT_SIZE)
        )

    elif signal_type == AssistantSignalType.RECORDING:
        duration = kwargs.get("duration", 0.0)
        is_active = kwargs.get("is_active", False)
        return RECORDING_STRUCT.pack(seq_num, signal_type.value, duration, is_active)

    elif signal_type == AssistantSignalType.TRANSCRIBING:
        partial_text = kwargs.get("partial_text", "")
        is_final = kwargs.get("is_final", False)
        return TRANSCRIBING_STRUCT.pack(
            seq_num,
            signal_type.value,
            _pad_string(partial_text, MAX_TEXT_SIZE),
            is_final,
        )

    elif signal_type == AssistantSignalType.EXECUTING:
        command = kwargs.get("command", "")
        return EXECUTING_STRUCT.pack(
            seq_num, signal_type.value, _pad_string(command, MAX_TEXT_SIZE)
        )

    elif signal_type == AssistantSignalType.ERROR:
        error_message = kwargs.get("error_message", "")
        error_type = kwargs.get("error_type", "")
        return ERROR_STRUCT.pack(
            seq_num,
            signal_type.value,
            _pad_string(error_message, MAX_ERROR_SIZE),
            _pad_string(error_type, MAX_TEXT_SIZE),
        )

    else:
        raise ValueError(f"Unknown signal type: {signal_type}")


def unpack_signal(data: bytes) -> SignalData:
    """Unpack binary struct into signal data.

    Args:
        data: Packed binary data

    Returns:
        SignalData with unpacked fields
    """
    # First 9 bytes are always seq_num (8) + signal_type (1)
    seq_num = struct.unpack("=Q", data[:8])[0]
    signal_type = AssistantSignalType(struct.unpack("=B", data[8:9])[0])

    if signal_type == AssistantSignalType.STATE_CHANGE:
        _, _, state_bytes = STATE_CHANGE_STRUCT.unpack(data[: STATE_CHANGE_STRUCT.size])
        return SignalData(
            signal_type=signal_type,
            seq_num=seq_num,
            data={"state": _unpad_string(state_bytes)},
        )

    elif signal_type == AssistantSignalType.WAKE_DETECTED:
        _, _, wake_word_bytes = WAKE_DETECTED_STRUCT.unpack(
            data[: WAKE_DETECTED_STRUCT.size]
        )
        return SignalData(
            signal_type=signal_type,
            seq_num=seq_num,
            data={"wake_word": _unpad_string(wake_word_bytes)},
        )

    elif signal_type == AssistantSignalType.RECORDING:
        _, _, duration, is_active = RECORDING_STRUCT.unpack(
            data[: RECORDING_STRUCT.size]
        )
        return SignalData(
            signal_type=signal_type,
            seq_num=seq_num,
            data={"duration": duration, "is_active": is_active},
        )

    elif signal_type == AssistantSignalType.TRANSCRIBING:
        _, _, partial_text_bytes, is_final = TRANSCRIBING_STRUCT.unpack(
            data[: TRANSCRIBING_STRUCT.size]
        )
        return SignalData(
            signal_type=signal_type,
            seq_num=seq_num,
            data={
                "partial_text": _unpad_string(partial_text_bytes),
                "is_final": is_final,
            },
        )

    elif signal_type == AssistantSignalType.EXECUTING:
        _, _, command_bytes = EXECUTING_STRUCT.unpack(data[: EXECUTING_STRUCT.size])
        return SignalData(
            signal_type=signal_type,
            seq_num=seq_num,
            data={"command": _unpad_string(command_bytes)},
        )

    elif signal_type == AssistantSignalType.ERROR:
        _, _, error_msg_bytes, error_type_bytes = ERROR_STRUCT.unpack(
            data[: ERROR_STRUCT.size]
        )
        return SignalData(
            signal_type=signal_type,
            seq_num=seq_num,
            data={
                "error_message": _unpad_string(error_msg_bytes),
                "error_type": _unpad_string(error_type_bytes),
            },
        )

    else:
        raise ValueError(f"Unknown signal type: {signal_type}")


def get_struct_size(signal_type: AssistantSignalType) -> int:
    """Get the size of a packed signal struct.

    Args:
        signal_type: Type of signal

    Returns:
        Size in bytes
    """
    struct_map = {
        AssistantSignalType.STATE_CHANGE: STATE_CHANGE_STRUCT,
        AssistantSignalType.WAKE_DETECTED: WAKE_DETECTED_STRUCT,
        AssistantSignalType.RECORDING: RECORDING_STRUCT,
        AssistantSignalType.TRANSCRIBING: TRANSCRIBING_STRUCT,
        AssistantSignalType.EXECUTING: EXECUTING_STRUCT,
        AssistantSignalType.ERROR: ERROR_STRUCT,
    }
    return struct_map[signal_type].size


def pack_ack(seq_num: int) -> bytes:
    """Pack ACK with sequence number.

    Args:
        seq_num: Sequence number to acknowledge

    Returns:
        Packed ACK data
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
        Size in bytes
    """
    return ACK_STRUCT.size


# Convenience wrapper functions for specific signal types
# (for backwards compatibility with tests)

def pack_state_change(seq_num: int, state: str) -> bytes:
    """Pack STATE_CHANGE signal."""
    return pack_signal(AssistantSignalType.STATE_CHANGE, seq_num, state=state)


def pack_wake_detected(seq_num: int, wake_word: str) -> bytes:
    """Pack WAKE_DETECTED signal."""
    return pack_signal(AssistantSignalType.WAKE_DETECTED, seq_num, wake_word=wake_word)


def pack_recording(seq_num: int, duration: float, is_active: bool) -> bytes:
    """Pack RECORDING signal."""
    return pack_signal(
        AssistantSignalType.RECORDING, seq_num, duration=duration, is_active=is_active
    )


def pack_transcribing(seq_num: int, partial_text: str, is_final: bool) -> bytes:
    """Pack TRANSCRIBING signal."""
    return pack_signal(
        AssistantSignalType.TRANSCRIBING,
        seq_num,
        partial_text=partial_text,
        is_final=is_final,
    )


def pack_executing(seq_num: int, command: str) -> bytes:
    """Pack EXECUTING signal."""
    return pack_signal(AssistantSignalType.EXECUTING, seq_num, command=command)


def pack_error(seq_num: int, error_message: str, error_type: str) -> bytes:
    """Pack ERROR signal."""
    return pack_signal(
        AssistantSignalType.ERROR,
        seq_num,
        error_message=error_message,
        error_type=error_type,
    )


def unpack_state_change(data: bytes) -> SignalData:
    """Unpack STATE_CHANGE signal."""
    return unpack_signal(data)


def unpack_wake_detected(data: bytes) -> SignalData:
    """Unpack WAKE_DETECTED signal."""
    return unpack_signal(data)


def unpack_recording(data: bytes) -> SignalData:
    """Unpack RECORDING signal."""
    return unpack_signal(data)


def unpack_transcribing(data: bytes) -> SignalData:
    """Unpack TRANSCRIBING signal."""
    return unpack_signal(data)


def unpack_executing(data: bytes) -> SignalData:
    """Unpack EXECUTING signal."""
    return unpack_signal(data)


def unpack_error(data: bytes) -> SignalData:
    """Unpack ERROR signal."""
    return unpack_signal(data)
