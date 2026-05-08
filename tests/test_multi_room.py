"""Tests for multi-room audio manager."""

from __future__ import annotations

import asyncio
import queue
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from champi_stt.core.multi_room import (
    MultiRoomAudioManager,
    RoomAudioChunk,
    RoomConfig,
    RoomStream,
)


class TestRoomConfig:
    def test_defaults(self) -> None:
        cfg = RoomConfig(name="living_room")
        assert cfg.device is None
        assert cfg.sample_rate == 16000
        assert cfg.channels == 1
        assert cfg.chunk_size == 4096

    def test_custom(self) -> None:
        cfg = RoomConfig(name="kitchen", device=1, sample_rate=44100)
        assert cfg.device == 1
        assert cfg.sample_rate == 44100


class TestRoomAudioChunk:
    def test_fields(self) -> None:
        audio = np.zeros(512, dtype=np.float32)
        chunk = RoomAudioChunk(room="kitchen", audio=audio)
        assert chunk.room == "kitchen"
        assert chunk.audio.shape == (512,)


class TestRoomStream:
    def test_start_raises_without_sounddevice(self) -> None:
        with patch("champi_stt.core.multi_room.SOUNDDEVICE_AVAILABLE", False):
            stream = RoomStream(RoomConfig("r"), on_chunk=lambda c: None)
            with pytest.raises(ImportError, match="sounddevice"):
                stream.start()

    def test_start_stop(self) -> None:
        mock_sd_stream = MagicMock()
        mock_sd_stream.active = True
        mock_sd = MagicMock()
        mock_sd.InputStream.return_value = mock_sd_stream

        with patch("champi_stt.core.multi_room.SOUNDDEVICE_AVAILABLE", True), \
             patch("champi_stt.core.multi_room.sd", mock_sd):
            stream = RoomStream(RoomConfig("room1", device=0), on_chunk=lambda c: None)
            stream.start()
            assert stream.is_active
            stream.stop()
            mock_sd_stream.stop.assert_called_once()
            mock_sd_stream.close.assert_called_once()

    def test_stop_when_not_started(self) -> None:
        stream = RoomStream(RoomConfig("r"), on_chunk=lambda c: None)
        stream.stop()  # should not raise

    def test_callback_invoked(self) -> None:
        received: list[RoomAudioChunk] = []

        mock_sd_stream = MagicMock()
        mock_sd_stream.active = True
        captured_callback: list = []

        def fake_input_stream(**kwargs):
            captured_callback.append(kwargs["callback"])
            return mock_sd_stream

        mock_sd = MagicMock()
        mock_sd.InputStream.side_effect = fake_input_stream
        with patch("champi_stt.core.multi_room.SOUNDDEVICE_AVAILABLE", True), \
             patch("champi_stt.core.multi_room.sd", mock_sd):
            stream = RoomStream(RoomConfig("r"), on_chunk=received.append)
            stream.start()

        indata = np.ones((512, 1), dtype=np.float32)
        captured_callback[0](indata, 512, None, None)
        assert len(received) == 1
        assert received[0].room == "r"


class TestMultiRoomAudioManager:
    def _make_mock_streams(self, *names: str):
        """Patch RoomStream.start/stop so no real audio device is needed."""
        mock_streams: dict[str, MagicMock] = {}

        original_init = RoomStream.__init__

        def fake_start(self_stream) -> None:
            self_stream._stream = MagicMock()
            self_stream._stream.active = True

        def fake_stop(self_stream) -> None:
            self_stream._stream = None

        return patch.multiple(RoomStream, start=fake_start, stop=fake_stop)

    @pytest.mark.asyncio
    async def test_start_creates_streams(self) -> None:
        rooms = [RoomConfig("a"), RoomConfig("b")]
        mgr = MultiRoomAudioManager(rooms)
        with patch.object(RoomStream, "start"), patch.object(RoomStream, "stop"):
            await mgr.start()
            assert set(mgr._streams.keys()) == {"a", "b"}
            await mgr.stop()

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(self) -> None:
        mgr = MultiRoomAudioManager([RoomConfig("a")])
        with patch.object(RoomStream, "start") as mock_start, \
             patch.object(RoomStream, "stop"):
            await mgr.start()
            await mgr.start()
            assert mock_start.call_count == 1
            await mgr.stop()

    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self) -> None:
        mgr = MultiRoomAudioManager([RoomConfig("a")])
        audio = np.zeros(512, dtype=np.float32)
        mgr._queue.put(RoomAudioChunk(room="a", audio=audio))
        mgr._running = True

        chunks = []
        async for chunk in mgr.stream():
            chunks.append(chunk)
            mgr._running = False

        assert len(chunks) == 1
        assert chunks[0].room == "a"

    @pytest.mark.asyncio
    async def test_active_rooms(self) -> None:
        mgr = MultiRoomAudioManager([])
        mock_stream = MagicMock()
        mock_stream.is_active = True
        mgr._streams["living"] = mock_stream
        assert mgr.active_rooms() == ["living"]

    def test_add_room_when_not_running(self) -> None:
        mgr = MultiRoomAudioManager([])
        with patch.object(RoomStream, "start") as mock_start:
            mgr.add_room(RoomConfig("new"))
            mock_start.assert_not_called()
        assert "new" in mgr._streams

    def test_add_room_duplicate_skipped(self) -> None:
        mgr = MultiRoomAudioManager([RoomConfig("dup")])
        with patch.object(RoomStream, "start"):
            mgr.add_room(RoomConfig("dup"))
        assert len([r for r in mgr._rooms if r.name == "dup"]) == 1

    def test_remove_room(self) -> None:
        mgr = MultiRoomAudioManager([RoomConfig("x")])
        mock_stream = MagicMock()
        mgr._streams["x"] = mock_stream
        mgr.remove_room("x")
        mock_stream.stop.assert_called_once()
        assert "x" not in mgr._streams

    def test_remove_nonexistent_room(self) -> None:
        mgr = MultiRoomAudioManager([])
        mgr.remove_room("ghost")  # should not raise
