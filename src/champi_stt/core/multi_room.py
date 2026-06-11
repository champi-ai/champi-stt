"""Multi-room audio: manage multiple simultaneous input device streams."""

from __future__ import annotations

import asyncio
import dataclasses
import queue
from collections.abc import AsyncIterator, Callable
from typing import Any

import numpy as np
from loguru import logger

try:
    import sounddevice as sd  # type: ignore[import-untyped]

    SOUNDDEVICE_AVAILABLE = True
except (ImportError, OSError):
    SOUNDDEVICE_AVAILABLE = False
    sd = None  # type: ignore[assignment]


@dataclasses.dataclass
class RoomConfig:
    """Configuration for a single audio input room.

    Attributes:
        name:        Unique room identifier (e.g. "living_room").
        device:      sounddevice device index or name (None = system default).
        sample_rate: Audio sample rate in Hz.
        channels:    Number of input channels.
        chunk_size:  Frames per callback.
    """

    name: str
    device: int | str | None = None
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 4096


@dataclasses.dataclass
class RoomAudioChunk:
    """An audio chunk tagged with its room of origin.

    Attributes:
        room:  Room name from RoomConfig.name.
        audio: Float32 numpy array of shape (frames, channels) or (frames,).
    """

    room: str
    audio: np.ndarray


AudioCallback = Callable[[RoomAudioChunk], None]


class RoomStream:
    """Manages a single sounddevice InputStream for one room."""

    def __init__(self, config: RoomConfig, on_chunk: AudioCallback) -> None:
        self.config = config
        self._on_chunk = on_chunk
        self._stream: Any = None

    def start(self) -> None:
        if not SOUNDDEVICE_AVAILABLE:
            raise ImportError("sounddevice is required for multi-room audio")

        def _callback(indata: np.ndarray, frames: int, time: Any, status: Any) -> None:
            if status:
                logger.warning(f"[{self.config.name}] audio callback status: {status}")
            audio: np.ndarray = indata.copy()
            self._on_chunk(RoomAudioChunk(room=self.config.name, audio=audio))

        self._stream = sd.InputStream(
            device=self.config.device,
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            blocksize=self.config.chunk_size,
            dtype="float32",
            callback=_callback,
        )
        self._stream.start()
        logger.info(
            f"Room '{self.config.name}' stream started (device={self.config.device})"
        )

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        logger.info(f"Room '{self.config.name}' stream stopped")

    @property
    def is_active(self) -> bool:
        return self._stream is not None and self._stream.active


class MultiRoomAudioManager:
    """Manages multiple simultaneous input device streams across rooms.

    Usage::

        manager = MultiRoomAudioManager([
            RoomConfig("living_room", device=0),
            RoomConfig("kitchen", device=1),
        ])
        await manager.start()
        async for chunk in manager.stream():
            print(chunk.room, chunk.audio.shape)
        await manager.stop()
    """

    def __init__(self, rooms: list[RoomConfig]) -> None:
        self._rooms = rooms
        self._streams: dict[str, RoomStream] = {}
        self._queue: queue.Queue[RoomAudioChunk] = queue.Queue()
        self._running = False

    async def start(self) -> None:
        """Start all room streams."""
        if self._running:
            return
        self._running = True
        for cfg in self._rooms:
            stream = RoomStream(cfg, on_chunk=self._queue.put)
            stream.start()
            self._streams[cfg.name] = stream

    async def stop(self) -> None:
        """Stop all room streams."""
        self._running = False
        for stream in self._streams.values():
            stream.stop()
        self._streams.clear()

    async def stream(self) -> AsyncIterator[RoomAudioChunk]:
        """Yield audio chunks from all rooms as they arrive."""
        loop = asyncio.get_running_loop()
        while self._running:
            try:
                chunk = await loop.run_in_executor(
                    None, lambda: self._queue.get(timeout=0.1)
                )
                yield chunk
            except queue.Empty:
                continue

    def active_rooms(self) -> list[str]:
        """Return names of currently active rooms."""
        return [name for name, s in self._streams.items() if s.is_active]

    def add_room(self, config: RoomConfig) -> None:
        """Add and start a new room stream at runtime."""
        if any(r.name == config.name for r in self._rooms):
            logger.warning(f"Room '{config.name}' already exists — skipping")
            return
        stream = RoomStream(config, on_chunk=self._queue.put)
        if self._running:
            stream.start()
        self._streams[config.name] = stream
        self._rooms.append(config)

    def remove_room(self, name: str) -> None:
        """Stop and remove a room stream by name."""
        stream = self._streams.pop(name, None)
        if stream:
            stream.stop()
        self._rooms = [r for r in self._rooms if r.name != name]
