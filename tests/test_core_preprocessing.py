"""Tests for core audio preprocessing utilities."""

import numpy as np
import pytest

from champi_stt.core.preprocessing import (
    convert_to_float32,
    convert_to_int16,
    get_audio_duration,
    get_audio_stats,
    normalize_audio,
    prepare_audio_for_stt,
    resample_audio,
)


class TestNormalizeAudio:
    @pytest.mark.asyncio
    async def test_float32_in_range(self):
        audio = np.array([0.5, -0.5, 0.25], dtype=np.float32)
        result = await normalize_audio(audio)
        assert result.dtype == np.float32
        assert np.max(np.abs(result)) <= 1.0

    @pytest.mark.asyncio
    async def test_int16_conversion(self):
        audio = np.array([16384, -16384], dtype=np.int16)
        result = await normalize_audio(audio)
        assert result.dtype == np.float32

    @pytest.mark.asyncio
    async def test_int32_conversion(self):
        audio = np.array([1073741824, -1073741824], dtype=np.int32)
        result = await normalize_audio(audio)
        assert result.dtype == np.float32

    @pytest.mark.asyncio
    async def test_other_dtype_becomes_float32(self):
        audio = np.array([0.1, 0.2], dtype=np.float64)
        result = await normalize_audio(audio)
        assert result.dtype == np.float32

    @pytest.mark.asyncio
    async def test_clipping_normalization(self):
        audio = np.array([2.0, -2.0, 1.0], dtype=np.float32)
        result = await normalize_audio(audio)
        assert np.max(np.abs(result)) <= 1.0 + 1e-6


class TestConvertToFloat32:
    @pytest.mark.asyncio
    async def test_already_float32_passthrough(self):
        audio = np.array([0.5, 0.3], dtype=np.float32)
        result = await convert_to_float32(audio)
        assert result is audio

    @pytest.mark.asyncio
    async def test_int16_to_float32(self):
        audio = np.array([0, 32767], dtype=np.int16)
        result = await convert_to_float32(audio)
        assert result.dtype == np.float32


class TestConvertToInt16:
    @pytest.mark.asyncio
    async def test_already_int16_passthrough(self):
        audio = np.array([100, -100], dtype=np.int16)
        result = await convert_to_int16(audio)
        assert result is audio

    @pytest.mark.asyncio
    async def test_float32_to_int16(self):
        audio = np.array([0.5, -0.5], dtype=np.float32)
        result = await convert_to_int16(audio)
        assert result.dtype == np.int16


class TestResampleAudio:
    @pytest.mark.asyncio
    async def test_same_rate_returns_input(self):
        audio = np.zeros(1600, dtype=np.float32)
        result = await resample_audio(audio, 16000, 16000)
        assert result is audio

    @pytest.mark.asyncio
    async def test_downsample(self):
        import importlib.util

        if importlib.util.find_spec("scipy") is None:
            pytest.skip("scipy not available")

        audio = np.zeros(16000, dtype=np.float32)
        result = await resample_audio(audio, 16000, 8000)
        assert len(result) == 8000


class TestPrepareAudioForSTT:
    @pytest.mark.asyncio
    async def test_float32_no_resample(self):
        audio = np.zeros(16000, dtype=np.float32)
        result = await prepare_audio_for_stt(audio, 16000, 16000, "float32")
        assert result.dtype == np.float32

    @pytest.mark.asyncio
    async def test_int16_output(self):
        audio = np.array([0.5, -0.5], dtype=np.float32)
        result = await prepare_audio_for_stt(audio, 16000, 16000, "int16")
        assert result.dtype == np.int16

    @pytest.mark.asyncio
    async def test_invalid_dtype_raises(self):
        audio = np.zeros(100, dtype=np.float32)
        with pytest.raises(ValueError, match="Unsupported"):
            await prepare_audio_for_stt(audio, 16000, 16000, "float16")


class TestGetAudioDuration:
    def test_duration_calculation(self):
        audio = np.zeros(16000)
        assert get_audio_duration(audio, 16000) == pytest.approx(1.0)

    def test_half_second(self):
        audio = np.zeros(8000)
        assert get_audio_duration(audio, 16000) == pytest.approx(0.5)


class TestGetAudioStats:
    def test_stats_keys(self):
        audio = np.array([0.5, -0.5, 0.0], dtype=np.float32)
        stats = get_audio_stats(audio)
        assert "shape" in stats
        assert "dtype" in stats
        assert "min" in stats
        assert "max" in stats
        assert "mean" in stats
        assert "rms" in stats
        assert "samples" in stats

    def test_stats_values(self):
        audio = np.array([1.0, -1.0], dtype=np.float32)
        stats = get_audio_stats(audio)
        assert stats["samples"] == 2
        assert stats["min"] == pytest.approx(-1.0)
        assert stats["max"] == pytest.approx(1.0)
        assert stats["mean"] == pytest.approx(0.0)
