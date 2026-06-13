"""Tests for speaker diarization module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from champi_stt.diarization.config import DiarizationConfig
from champi_stt.diarization.diarizer import DiarizationSegment, Diarizer


class TestDiarizationConfig:
    def test_defaults(self) -> None:
        cfg = DiarizationConfig()
        assert cfg.hf_token is None
        assert cfg.num_speakers is None
        assert cfg.model == "pyannote/speaker-diarization-3.1"
        assert cfg.device == "cpu"

    def test_from_env_hf_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HF_TOKEN", "tok123")
        cfg = DiarizationConfig.from_env()
        assert cfg.hf_token == "tok123"

    def test_from_env_huggingface_token_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "tok456")
        cfg = DiarizationConfig.from_env()
        assert cfg.hf_token == "tok456"

    def test_from_env_no_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)
        cfg = DiarizationConfig.from_env()
        assert cfg.hf_token is None


class TestDiarizationSegment:
    def test_fields(self) -> None:
        seg = DiarizationSegment(
            speaker_id="SPEAKER_00", start=0.5, end=2.0, text="hello"
        )
        assert seg.speaker_id == "SPEAKER_00"
        assert seg.start == 0.5
        assert seg.end == 2.0
        assert seg.text == "hello"

    def test_default_text(self) -> None:
        seg = DiarizationSegment(speaker_id="SPEAKER_01", start=0.0, end=1.0)
        assert seg.text == ""


class TestDiarizer:
    def test_init_default_config(self) -> None:
        d = Diarizer()
        assert d.config.model == "pyannote/speaker-diarization-3.1"

    @pytest.mark.asyncio
    async def test_initialize_raises_without_pyannote(self) -> None:
        with patch("champi_stt.diarization.diarizer.PYANNOTE_AVAILABLE", False):
            d = Diarizer()
            with pytest.raises(ImportError, match="pyannote"):
                await d.initialize()

    @pytest.mark.asyncio
    async def test_diarize_raises_before_initialize(self) -> None:
        d = Diarizer()
        with pytest.raises(RuntimeError, match="initialize"):
            await d.diarize(np.zeros(1024, dtype=np.float32))

    @pytest.mark.asyncio
    async def test_diarize_with_mock_pipeline(self, tmp_path: Path) -> None:
        mock_turn1 = MagicMock()
        mock_turn1.start = 0.0
        mock_turn1.end = 1.5
        mock_turn2 = MagicMock()
        mock_turn2.start = 1.5
        mock_turn2.end = 3.0

        mock_annotation = MagicMock()
        mock_annotation.itertracks.return_value = [
            (mock_turn1, None, "SPEAKER_00"),
            (mock_turn2, None, "SPEAKER_01"),
        ]

        mock_pipeline = MagicMock(return_value=mock_annotation)
        mock_pipeline_cls = MagicMock()
        mock_pipeline_cls.from_pretrained.return_value = mock_pipeline

        with (
            patch("champi_stt.diarization.diarizer.PYANNOTE_AVAILABLE", True),
            patch("champi_stt.diarization.diarizer.Pipeline", mock_pipeline_cls),
            patch(
                "champi_stt.diarization.diarizer.Diarizer._to_wav_path",
                return_value="/tmp/x.wav",
            ),
        ):
            d = Diarizer(DiarizationConfig(hf_token="tok"))
            await d.initialize()
            audio = np.zeros(16000, dtype=np.float32)
            segments = await d.diarize(audio)

        assert len(segments) == 2
        assert segments[0].speaker_id == "SPEAKER_00"
        assert segments[1].speaker_id == "SPEAKER_01"

    @pytest.mark.asyncio
    async def test_shutdown_clears_pipeline(self) -> None:
        d = Diarizer()
        d._pipeline = MagicMock()
        await d.shutdown()
        assert d._pipeline is None

    def test_annotate_transcription(self) -> None:
        segs = [
            DiarizationSegment("SPEAKER_00", 0.0, 1.0),
            DiarizationSegment("SPEAKER_01", 1.0, 2.0),
        ]
        result = Diarizer().annotate_transcription(segs, "Hello world. How are you?")
        assert result[0].text == "Hello world."
        assert result[1].text == "How are you?"

    def test_annotate_fewer_parts_than_segments(self) -> None:
        segs = [
            DiarizationSegment("SPEAKER_00", 0.0, 1.0),
            DiarizationSegment("SPEAKER_01", 1.0, 2.0),
        ]
        result = Diarizer().annotate_transcription(segs, "Only one sentence.")
        assert result[0].text == "Only one sentence."
        assert result[1].text == ""

    def test_to_wav_path_string(self) -> None:
        path = Diarizer._to_wav_path("/some/file.wav", 16000)
        assert path == "/some/file.wav"

    def test_to_wav_path_pathlib(self, tmp_path: Path) -> None:
        p = tmp_path / "audio.wav"
        result = Diarizer._to_wav_path(p, 16000)
        assert result == str(p)
