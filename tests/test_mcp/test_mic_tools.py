"""Unit tests for the internal audio bridge helper in mic_tools.

Tests cover:
- ``_check_sounddevice`` availability guard
- ``_audio_to_text`` WAV write, provider pipeline, text extraction, and cleanup
- ``listen_once`` fixed-duration recording
- ``listen_until_silence`` silence-detection recording
- ``list_audio_devices`` device enumeration
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from champi_stt.core.response import TranscriptionResponse

# ---------------------------------------------------------------------------
# _check_sounddevice
# ---------------------------------------------------------------------------


class TestCheckSounddevice:
    def test_passes_when_sounddevice_is_importable(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        with patch.dict("sys.modules", {"sounddevice": MagicMock()}):
            mic._check_sounddevice()  # must not raise

    def test_raises_import_error_when_sounddevice_missing(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        with (
            patch.dict("sys.modules", {"sounddevice": None}),
            pytest.raises(ImportError, match="sounddevice"),
        ):
            mic._check_sounddevice()

    def test_error_message_mentions_portaudio(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        with (
            patch.dict("sys.modules", {"sounddevice": None}),
            pytest.raises(ImportError, match="PortAudio"),
        ):
            mic._check_sounddevice()

    def test_original_exception_is_chained(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        with (
            patch.dict(sys.modules, {"sounddevice": None}),
            pytest.raises(ImportError) as exc_info,
        ):
            mic._check_sounddevice()
        assert exc_info.value.__cause__ is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider(
    *,
    transcribe_result: str | dict | TranscriptionResponse = TranscriptionResponse(
        text="hello world"
    ),
    transcribe_raises: Exception | None = None,
    initialize_raises: Exception | None = None,
) -> MagicMock:
    """Build a mock STT provider."""
    prov = MagicMock()
    prov.initialize = AsyncMock(side_effect=initialize_raises)
    prov.transcribe = AsyncMock(
        side_effect=transcribe_raises, return_value=transcribe_result
    )
    return prov


# ---------------------------------------------------------------------------
# _audio_to_text
# ---------------------------------------------------------------------------


class TestAudioToText:
    """Tests for the async _audio_to_text helper."""

    def _make_audio(self, n: int = 1600) -> np.ndarray:
        """Return a short silent int16 numpy array."""
        return np.zeros(n, dtype=np.int16)

    @pytest.mark.asyncio
    async def test_returns_text_from_transcription_response(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        prov = _make_provider(transcribe_result=TranscriptionResponse(text="test text"))
        with (
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
        ):
            result = await mic._audio_to_text(
                self._make_audio(), 16000, None, "whisperlive"
            )
        assert result == "test text"

    @pytest.mark.asyncio
    async def test_returns_text_from_dict_result(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        prov = _make_provider(transcribe_result={"text": "dict result", "lang": "en"})
        with (
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
        ):
            result = await mic._audio_to_text(
                self._make_audio(), 16000, None, "whisperlive"
            )
        assert result == "dict result"

    @pytest.mark.asyncio
    async def test_returns_str_result_directly(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        prov = _make_provider(transcribe_result="plain string")
        with (
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
        ):
            result = await mic._audio_to_text(
                self._make_audio(), 16000, None, "whisperlive"
            )
        assert result == "plain string"

    @pytest.mark.asyncio
    async def test_defaults_to_whisperlive_when_provider_name_is_none(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        prov = _make_provider()
        with (
            patch(
                "champi_stt.mcp.mic_tools.get_provider", return_value=prov
            ) as mock_get,
            patch("champi_stt.mcp.mic_tools.sf.write"),
        ):
            await mic._audio_to_text(self._make_audio(), 16000, None, None)
        mock_get.assert_called_once_with("whisperlive")

    @pytest.mark.asyncio
    async def test_uses_champi_stt_provider_env_var_when_provider_name_is_none(
        self,
    ) -> None:
        import champi_stt.mcp.mic_tools as mic

        prov = _make_provider()
        with (
            patch(
                "champi_stt.mcp.mic_tools.get_provider", return_value=prov
            ) as mock_get,
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch.dict(os.environ, {"CHAMPI_STT_PROVIDER": "openai_whisper"}),
        ):
            await mic._audio_to_text(self._make_audio(), 16000, None, None)
        mock_get.assert_called_once_with("openai_whisper")

    @pytest.mark.asyncio
    async def test_explicit_provider_name_overrides_env_var(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        prov = _make_provider()
        with (
            patch(
                "champi_stt.mcp.mic_tools.get_provider", return_value=prov
            ) as mock_get,
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch.dict(os.environ, {"CHAMPI_STT_PROVIDER": "openai_whisper"}),
        ):
            await mic._audio_to_text(self._make_audio(), 16000, None, "whisperlive")
        mock_get.assert_called_once_with("whisperlive")

    @pytest.mark.asyncio
    async def test_uses_specified_provider_name(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        prov = _make_provider()
        with (
            patch(
                "champi_stt.mcp.mic_tools.get_provider", return_value=prov
            ) as mock_get,
            patch("champi_stt.mcp.mic_tools.sf.write"),
        ):
            await mic._audio_to_text(self._make_audio(), 16000, None, "openai_whisper")
        mock_get.assert_called_once_with("openai_whisper")

    @pytest.mark.asyncio
    async def test_provider_initialize_is_called(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        prov = _make_provider()
        with (
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
        ):
            await mic._audio_to_text(self._make_audio(), 16000, None, "whisperlive")
        prov.initialize.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_language_hint_passed_to_transcribe(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        prov = _make_provider()
        with (
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
        ):
            await mic._audio_to_text(self._make_audio(), 16000, "fr", "whisperlive")
        _, kwargs = prov.transcribe.call_args
        assert kwargs.get("language") == "fr"

    @pytest.mark.asyncio
    async def test_temp_file_is_deleted_after_success(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        captured_path: list[str] = []
        original_remove = os.remove

        def _capture_remove(path: str) -> None:
            captured_path.append(path)
            original_remove(path)

        prov = _make_provider()
        with (
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove", side_effect=_capture_remove),
        ):
            await mic._audio_to_text(self._make_audio(), 16000, None, "whisperlive")
        assert len(captured_path) == 1
        assert captured_path[0].endswith(".wav")

    @pytest.mark.asyncio
    async def test_temp_file_is_deleted_even_when_transcription_fails(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        removed: list[str] = []
        prov = _make_provider(transcribe_raises=RuntimeError("model error"))
        with (
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch(
                "champi_stt.mcp.mic_tools.os.remove",
                side_effect=lambda p: removed.append(p),
            ),
            pytest.raises(RuntimeError, match="model error"),
        ):
            await mic._audio_to_text(self._make_audio(), 16000, None, "whisperlive")
        assert len(removed) == 1

    @pytest.mark.asyncio
    async def test_temp_file_cleanup_survives_missing_file(self) -> None:
        """Cleanup must not raise if the temp file was already removed."""
        import champi_stt.mcp.mic_tools as mic

        prov = _make_provider()
        with (
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch(
                "champi_stt.mcp.mic_tools.os.remove",
                side_effect=FileNotFoundError,
            ),
        ):
            result = await mic._audio_to_text(
                self._make_audio(), 16000, None, "whisperlive"
            )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_sf_write_called_with_wav_suffix(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        prov = _make_provider()
        written_paths: list[str] = []

        def _capture_write(path: str, *args: object, **kwargs: object) -> None:
            written_paths.append(path)

        with (
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write", side_effect=_capture_write),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            await mic._audio_to_text(self._make_audio(), 16000, None, "whisperlive")
        assert len(written_paths) == 1
        assert written_paths[0].endswith(".wav")

    @pytest.mark.asyncio
    async def test_sf_write_called_with_sample_rate(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        prov = _make_provider()
        write_args: list[tuple] = []

        def _capture_write(*args: object, **kwargs: object) -> None:
            write_args.append(args)

        with (
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write", side_effect=_capture_write),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            await mic._audio_to_text(self._make_audio(), 44100, None, "whisperlive")
        assert write_args[0][2] == 44100


# ---------------------------------------------------------------------------
# listen_once
# ---------------------------------------------------------------------------


def _make_sd_mock(*, num_frames: int = 16000) -> MagicMock:
    """Return a mock sounddevice module with rec(), wait(), and InputStream stubs."""
    sd = MagicMock()
    audio = np.zeros((num_frames, 1), dtype=np.int16)
    sd.rec.return_value = audio
    sd.wait.return_value = None

    # InputStream context manager: stream.read() returns (frame, False)
    frame = np.zeros((480, 1), dtype=np.int16)
    mock_stream = MagicMock()
    mock_stream.read.return_value = (frame, False)
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    sd.InputStream.return_value = mock_stream
    sd.default = MagicMock()
    sd.default.device = [0, 0]
    return sd


class TestListenOnce:
    """Tests for the async listen_once public function."""

    @pytest.mark.asyncio
    async def test_returns_transcription_text(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock()
        prov = _make_provider(transcribe_result=TranscriptionResponse(text="hello mic"))
        with (
            patch.dict("sys.modules", {"sounddevice": sd}),
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            result = await mic.listen_once()
        assert result == "hello mic"

    @pytest.mark.asyncio
    async def test_rec_called_with_correct_frame_count(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock(num_frames=int(3.0 * 16000))
        prov = _make_provider()
        with (
            patch.dict("sys.modules", {"sounddevice": sd}),
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            await mic.listen_once(duration_seconds=3.0)
        sd.rec.assert_called_once()
        call_args = sd.rec.call_args
        assert call_args[0][0] == int(3.0 * 16000)

    @pytest.mark.asyncio
    async def test_rec_uses_16000_samplerate(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock()
        prov = _make_provider()
        with (
            patch.dict("sys.modules", {"sounddevice": sd}),
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            await mic.listen_once()
        _, kwargs = sd.rec.call_args
        assert kwargs["samplerate"] == 16000

    @pytest.mark.asyncio
    async def test_rec_uses_mono_channel(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock()
        prov = _make_provider()
        with (
            patch.dict("sys.modules", {"sounddevice": sd}),
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            await mic.listen_once()
        _, kwargs = sd.rec.call_args
        assert kwargs["channels"] == 1

    @pytest.mark.asyncio
    async def test_rec_uses_int16_dtype(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock()
        prov = _make_provider()
        with (
            patch.dict("sys.modules", {"sounddevice": sd}),
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            await mic.listen_once()
        _, kwargs = sd.rec.call_args
        assert kwargs["dtype"] == "int16"

    @pytest.mark.asyncio
    async def test_wait_is_called_after_rec(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock()
        prov = _make_provider()
        with (
            patch.dict("sys.modules", {"sounddevice": sd}),
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            await mic.listen_once()
        sd.wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_sounddevice_returns_error_string(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        with patch.dict("sys.modules", {"sounddevice": None}):
            result = await mic.listen_once()
        assert result.startswith("error:")
        assert "ImportError" in result

    @pytest.mark.asyncio
    async def test_transcription_error_returns_error_string(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock()
        prov = _make_provider(transcribe_raises=RuntimeError("model crash"))
        with (
            patch.dict("sys.modules", {"sounddevice": sd}),
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            result = await mic.listen_once()
        assert result.startswith("error:")
        assert "RuntimeError" in result
        assert "model crash" in result

    @pytest.mark.asyncio
    async def test_language_forwarded_to_audio_to_text(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock()
        prov = _make_provider()
        with (
            patch.dict("sys.modules", {"sounddevice": sd}),
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            await mic.listen_once(language="es")
        _, kwargs = prov.transcribe.call_args
        assert kwargs.get("language") == "es"

    @pytest.mark.asyncio
    async def test_provider_forwarded_to_audio_to_text(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock()
        prov = _make_provider()
        with (
            patch.dict("sys.modules", {"sounddevice": sd}),
            patch(
                "champi_stt.mcp.mic_tools.get_provider", return_value=prov
            ) as mock_get,
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            await mic.listen_once(provider="openai_whisper")
        mock_get.assert_called_once_with("openai_whisper")


# ---------------------------------------------------------------------------
# listen_until_silence
# ---------------------------------------------------------------------------


class TestListenUntilSilence:
    """Tests for the async listen_until_silence public function."""

    @pytest.mark.asyncio
    async def test_returns_transcription_text(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock()
        prov = _make_provider(
            transcribe_result=TranscriptionResponse(text="silence mic")
        )
        # Mock webrtcvad so all frames are silent → loop exits on silence_threshold
        mock_vad = MagicMock()
        mock_vad.is_speech.return_value = False
        mock_vad_cls = MagicMock(return_value=mock_vad)
        mock_webrtcvad = MagicMock()
        mock_webrtcvad.Vad = mock_vad_cls
        with (
            patch.dict("sys.modules", {"sounddevice": sd, "webrtcvad": mock_webrtcvad}),
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            result = await mic.listen_until_silence(
                max_duration_seconds=10.0, silence_threshold_ms=500
            )
        assert result == "silence mic"

    def _silence_vad_mock(self) -> MagicMock:
        """Return a webrtcvad module mock where all frames are silent."""
        mock_vad = MagicMock()
        mock_vad.is_speech.return_value = False
        mock_webrtcvad = MagicMock()
        mock_webrtcvad.Vad.return_value = mock_vad
        return mock_webrtcvad

    @pytest.mark.asyncio
    async def test_inputstream_opened_with_correct_params(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock()
        prov = _make_provider()
        wvad = self._silence_vad_mock()
        with (
            patch.dict("sys.modules", {"sounddevice": sd, "webrtcvad": wvad}),
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            await mic.listen_until_silence(
                max_duration_seconds=10.0, silence_threshold_ms=500
            )
        sd.InputStream.assert_called_once()
        _, kwargs = sd.InputStream.call_args
        assert kwargs.get("samplerate") == 16000
        assert kwargs.get("channels") == 1
        assert kwargs.get("dtype") == "int16"

    @pytest.mark.asyncio
    async def test_missing_sounddevice_returns_error_string(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        with patch.dict("sys.modules", {"sounddevice": None}):
            result = await mic.listen_until_silence(
                max_duration_seconds=10.0, silence_threshold_ms=500
            )
        assert result.startswith("error:")
        assert "ImportError" in result

    @pytest.mark.asyncio
    async def test_language_forwarded(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock()
        prov = _make_provider()
        wvad = self._silence_vad_mock()
        with (
            patch.dict("sys.modules", {"sounddevice": sd, "webrtcvad": wvad}),
            patch("champi_stt.mcp.mic_tools.get_provider", return_value=prov),
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            await mic.listen_until_silence(
                max_duration_seconds=5.0, silence_threshold_ms=300, language="it"
            )
        _, kwargs = prov.transcribe.call_args
        assert kwargs.get("language") == "it"

    @pytest.mark.asyncio
    async def test_provider_forwarded(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = _make_sd_mock()
        prov = _make_provider()
        wvad = self._silence_vad_mock()
        with (
            patch.dict("sys.modules", {"sounddevice": sd, "webrtcvad": wvad}),
            patch(
                "champi_stt.mcp.mic_tools.get_provider", return_value=prov
            ) as mock_get,
            patch("champi_stt.mcp.mic_tools.sf.write"),
            patch("champi_stt.mcp.mic_tools.os.remove"),
        ):
            await mic.listen_until_silence(
                max_duration_seconds=5.0,
                silence_threshold_ms=300,
                provider="openai_whisper",
            )
        mock_get.assert_called_once_with("openai_whisper")


# ---------------------------------------------------------------------------
# list_audio_devices
# ---------------------------------------------------------------------------


class TestListAudioDevices:
    """Tests for the list_audio_devices function."""

    def test_returns_list_of_dicts(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = MagicMock()
        sd.query_devices.return_value = [
            {
                "name": "Built-in Mic",
                "max_input_channels": 1,
                "default_samplerate": 44100.0,
            },
        ]
        with patch.dict("sys.modules", {"sounddevice": sd}):
            result = mic.list_audio_devices()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_device_entry_has_expected_keys(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = MagicMock()
        sd.query_devices.return_value = [
            {
                "name": "Built-in Mic",
                "max_input_channels": 2,
                "default_samplerate": 48000.0,
            },
        ]
        with patch.dict("sys.modules", {"sounddevice": sd}):
            result = mic.list_audio_devices()
        device = result[0]
        assert "index" in device
        assert "name" in device
        assert "max_input_channels" in device
        assert "default_samplerate" in device

    def test_output_only_devices_are_excluded(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        sd = MagicMock()
        sd.query_devices.return_value = [
            {
                "name": "Speakers",
                "max_input_channels": 0,
                "default_samplerate": 44100.0,
            },
        ]
        with patch.dict("sys.modules", {"sounddevice": sd}):
            result = mic.list_audio_devices()
        assert result == []

    def test_missing_sounddevice_raises_import_error(self) -> None:
        import champi_stt.mcp.mic_tools as mic

        with (
            patch.dict("sys.modules", {"sounddevice": None}),
            pytest.raises(ImportError, match="sounddevice"),
        ):
            mic.list_audio_devices()
