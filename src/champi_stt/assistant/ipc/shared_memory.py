"""Shared memory manager for assistant IPC."""

from multiprocessing import shared_memory

from loguru import logger

from .structs import (
    AssistantSignalType,
    get_ack_size,
    get_struct_size,
    pack_ack,
    unpack_ack,
)


def cleanup_orphaned_regions(name_prefix: str = "champi_assistant") -> list[str]:
    """Clean up orphaned shared memory regions.

    This utility function removes shared memory regions that were left behind
    by crashed processes or improper shutdowns.

    Args:
        name_prefix: Memory region prefix to clean up

    Returns:
        List of cleaned region names
    """
    cleaned_regions = []

    for signal_type in AssistantSignalType:
        # Try to clean up data region
        region_name = f"{name_prefix}_{signal_type.name.lower()}"
        try:
            shm = shared_memory.SharedMemory(name=region_name)
            shm.close()
            shm.unlink()
            cleaned_regions.append(region_name)
            logger.info(f"Cleaned up orphaned region: {region_name}")
        except FileNotFoundError:
            # Region doesn't exist, skip
            pass
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
            # Region doesn't exist, skip
            pass
        except Exception as e:
            logger.warning(f"Failed to clean up {ack_region_name}: {e}")

    return cleaned_regions


class AssistantSharedMemoryManager:
    """Manages shared memory regions for assistant signal types."""

    def __init__(self, name_prefix: str = "champi_assistant"):
        """Initialize shared memory manager.

        Args:
            name_prefix: Prefix for shared memory region names
        """
        self.name_prefix = name_prefix
        self.memory_regions: dict[AssistantSignalType, shared_memory.SharedMemory] = {}
        self.ack_regions: dict[AssistantSignalType, shared_memory.SharedMemory] = {}
        self.is_creator = False

    def create_regions(self):
        """Create shared memory regions for all signal types (data + ACK)."""
        self.is_creator = True

        for signal_type in AssistantSignalType:
            # Create data region
            region_name = f"{self.name_prefix}_{signal_type.name.lower()}"
            size = get_struct_size(signal_type)

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
                logger.error(
                    f"Failed to create shared memory region {region_name}: {e}"
                )
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
                logger.debug(
                    f"Created ACK region: {ack_region_name} ({ack_size} bytes)"
                )

            except Exception as e:
                logger.error(f"Failed to create ACK region {ack_region_name}: {e}")
                raise

    def attach_regions(self):
        """Attach to existing shared memory regions (data + ACK)."""
        self.is_creator = False

        for signal_type in AssistantSignalType:
            # Attach to data region
            region_name = f"{self.name_prefix}_{signal_type.name.lower()}"

            try:
                shm = shared_memory.SharedMemory(name=region_name)
                self.memory_regions[signal_type] = shm
                logger.debug(f"Attached to shared memory region: {region_name}")

            except FileNotFoundError:
                logger.error(f"Shared memory region not found: {region_name}")
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

    def write_signal(self, signal_type: AssistantSignalType, data: bytes):
        """Write signal data to appropriate memory region.

        Args:
            signal_type: Type of signal
            data: Packed signal data
        """
        if signal_type not in self.memory_regions:
            raise ValueError(f"No memory region for signal type: {signal_type}")

        shm = self.memory_regions[signal_type]
        expected_size = get_struct_size(signal_type)

        if len(data) != expected_size:
            raise ValueError(
                f"Data size mismatch: expected {expected_size}, got {len(data)}"
            )

        # Write to shared memory
        shm.buf[:expected_size] = data

    def read_signal(self, signal_type: AssistantSignalType) -> bytes:
        """Read signal data from memory region.

        Args:
            signal_type: Type of signal

        Returns:
            Packed signal data
        """
        if signal_type not in self.memory_regions:
            raise ValueError(f"No memory region for signal type: {signal_type}")

        shm = self.memory_regions[signal_type]
        size = get_struct_size(signal_type)

        return bytes(shm.buf[:size])

    def write_ack(self, signal_type: AssistantSignalType, seq_num: int):
        """Write ACK with sequence number to ACK region.

        Args:
            signal_type: Type of signal
            seq_num: Sequence number to acknowledge
        """
        if signal_type not in self.ack_regions:
            raise ValueError(f"No ACK region for signal type: {signal_type}")

        ack_data = pack_ack(seq_num)
        ack_shm = self.ack_regions[signal_type]
        ack_shm.buf[: len(ack_data)] = ack_data

    def read_ack(self, signal_type: AssistantSignalType) -> int:
        """Read ACK sequence number from ACK region.

        Args:
            signal_type: Type of signal

        Returns:
            Sequence number
        """
        if signal_type not in self.ack_regions:
            raise ValueError(f"No ACK region for signal type: {signal_type}")

        ack_shm = self.ack_regions[signal_type]
        ack_size = get_ack_size()
        ack_data = bytes(ack_shm.buf[:ack_size])
        return unpack_ack(ack_data)

    def cleanup(self):
        """Close and optionally unlink shared memory regions (data + ACK)."""
        # Cleanup data regions
        for signal_type, shm in self.memory_regions.items():
            try:
                shm.close()

                # Only unlink if we created the regions
                if self.is_creator:
                    shm.unlink()
                    logger.debug(
                        f"Cleaned up shared memory: {self.name_prefix}_{signal_type.name.lower()}"
                    )

            except Exception as e:
                logger.error(f"Error cleaning up shared memory for {signal_type}: {e}")

        self.memory_regions.clear()

        # Cleanup ACK regions
        for signal_type, ack_shm in self.ack_regions.items():
            try:
                ack_shm.close()

                # Only unlink if we created the regions
                if self.is_creator:
                    ack_shm.unlink()
                    logger.debug(
                        f"Cleaned up ACK region: {self.name_prefix}_{signal_type.name.lower()}_ack"
                    )

            except Exception as e:
                logger.error(f"Error cleaning up ACK region for {signal_type}: {e}")

        self.ack_regions.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
