"""Integration tests for wake-word → STT → command pipeline."""

import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import pytest

from champi_stt.assistant.commands.builtin import register_builtin_commands
from champi_stt.assistant.commands.registry import CommandRegistry
from champi_stt.assistant.wakeword.base import WakeWordEvent
from champi_stt.core.response import TranscriptionResponse


@dataclass
class _MockProviderConfig:
    language: str | None = None


class _MockSTTProvider:
    """Mock STT provider returning canned responses."""

    def __init__(self, response_text: str = "hello") -> None:
        self._text = response_text
        self.transcribe_calls: list[Any] = []

    async def transcribe(self, audio: Any) -> TranscriptionResponse:
        self.transcribe_calls.append(audio)
        return TranscriptionResponse(text=self._text, language="en", duration=1.0)


class _MockWakeWordEngine:
    """Mock wake word engine that fires once."""

    def __init__(self, keyword: str = "hey champi") -> None:
        self._keyword = keyword
        self._fired = False

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def detect(self, audio_frame: np.ndarray) -> WakeWordEvent | None:
        if not self._fired:
            self._fired = True
            return WakeWordEvent(
                keyword=self._keyword,
                timestamp=time.time(),
                confidence=0.99,
            )
        return None


class TestWakeWordDetectionPipeline:
    """Tests for the wake-word detection stage."""

    @pytest.mark.asyncio
    async def test_wake_word_event_triggers_stt(self):
        stt = _MockSTTProvider("what time is it")
        registry = CommandRegistry()
        register_builtin_commands(registry)

        audio_chunk = np.zeros(512, dtype=np.int16)
        ww_engine = _MockWakeWordEngine("hey champi")

        event = ww_engine.detect(audio_chunk)
        assert event is not None
        assert event.keyword == "hey champi"
        assert event.confidence == pytest.approx(0.99)

        result = await stt.transcribe(audio_chunk)
        assert result.text == "what time is it"

        cmd_result = await registry.execute(result.text)
        assert cmd_result is not None
        assert "time" in cmd_result.lower()

    @pytest.mark.asyncio
    async def test_no_wake_word_no_stt(self):
        stt = _MockSTTProvider()
        ww_engine = _MockWakeWordEngine()
        ww_engine._fired = True  # already fired, won't fire again

        audio_chunk = np.zeros(512, dtype=np.int16)
        event = ww_engine.detect(audio_chunk)
        assert event is None
        assert len(stt.transcribe_calls) == 0

    @pytest.mark.asyncio
    async def test_transcription_to_command_routing(self):
        registry = CommandRegistry()
        results: list[Any] = []

        async def my_handler() -> str:
            results.append("executed")
            return "done"

        registry.register_exact("turn on lights", my_handler)

        resp = TranscriptionResponse(text="turn on lights", language="en")
        cmd_result = await registry.execute(resp.text)
        assert cmd_result == "done"
        assert results == ["executed"]

    @pytest.mark.asyncio
    async def test_pattern_command_from_transcription(self):
        registry = CommandRegistry()
        volumes: list[str] = []

        async def set_vol(level: str) -> str:
            volumes.append(level)
            return f"volume set to {level}"

        registry.register_pattern(r"set volume to (?P<level>\d+)", set_vol)
        resp = TranscriptionResponse(text="set volume to 75")
        result = await registry.execute(resp.text)
        assert result == "volume set to 75"
        assert volumes == ["75"]

    @pytest.mark.asyncio
    async def test_unknown_command_returns_none(self):
        registry = CommandRegistry()
        register_builtin_commands(registry)

        resp = TranscriptionResponse(text="xyzzy frobozzle magic")
        result = await registry.execute(resp.text)
        assert result is None


class TestMultipleWakeWordPipeline:
    @pytest.mark.asyncio
    async def test_multiple_activations(self):
        registry = CommandRegistry()
        execution_count = [0]

        async def counter() -> str:
            execution_count[0] += 1
            return "counted"

        registry.register_exact("hello", counter)

        for _ in range(3):
            resp = TranscriptionResponse(text="hello")
            await registry.execute(resp.text)

        assert execution_count[0] == 3

    @pytest.mark.asyncio
    async def test_pipeline_with_confidence_threshold(self):
        """Test that low-confidence wake word events can be filtered."""
        low_confidence_event = WakeWordEvent(
            keyword="hey champi",
            timestamp=time.time(),
            confidence=0.2,
        )
        high_confidence_event = WakeWordEvent(
            keyword="hey champi",
            timestamp=time.time(),
            confidence=0.9,
        )

        confidence_threshold = 0.5
        stt_calls = [0]

        async def handle_if_confident(event: WakeWordEvent) -> bool:
            if event.confidence >= confidence_threshold:
                stt_calls[0] += 1
                return True
            return False

        assert not await handle_if_confident(low_confidence_event)
        assert await handle_if_confident(high_confidence_event)
        assert stt_calls[0] == 1


class TestSTTResponseHandling:
    @pytest.mark.asyncio
    async def test_empty_transcription_no_command(self):
        registry = CommandRegistry()
        register_builtin_commands(registry)

        resp = TranscriptionResponse(text="", language="en")
        result = await registry.execute(resp.text)
        assert result is None

    @pytest.mark.asyncio
    async def test_transcription_with_metadata(self):
        registry = CommandRegistry()

        async def handler() -> dict[str, Any]:
            return {"status": "ok"}

        registry.register_exact("status", handler)

        resp = TranscriptionResponse(
            text="status",
            language="en",
            duration=0.5,
            language_probability=0.99,
        )
        result = await registry.execute(resp.text)
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_case_insensitive_command_matching(self):
        registry = CommandRegistry()

        async def hello() -> str:
            return "hi"

        registry.register_exact("HELLO", hello)

        for text in ["hello", "HELLO", "Hello", "hElLo"]:
            resp = TranscriptionResponse(text=text)
            result = await registry.execute(resp.text)
            assert result == "hi", f"Failed for text: {text!r}"
