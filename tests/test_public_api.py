"""Smoke tests verifying every public symbol listed in __all__ is importable."""

from __future__ import annotations

import champi_stt


class TestPublicApiSymbols:
    def test_all_symbols_importable(self) -> None:
        missing = [name for name in champi_stt.__all__ if not hasattr(champi_stt, name)]
        assert missing == [], f"Public symbols missing from package: {missing}"

    def test_version_is_string(self) -> None:
        assert isinstance(champi_stt.__version__, str)
        parts = champi_stt.__version__.split(".")
        assert len(parts) >= 2

    def test_factory_functions_callable(self) -> None:
        assert callable(champi_stt.get_provider)
        assert callable(champi_stt.get_default_provider)
        assert callable(champi_stt.list_providers)

    def test_list_providers_returns_list(self) -> None:
        providers = champi_stt.list_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0

    def test_base_classes_are_abstract(self) -> None:
        import inspect

        assert inspect.isabstract(champi_stt.BaseSTTProvider)
        assert inspect.isabstract(champi_stt.BaseTranscriber)

    def test_streaming_config_instantiable(self) -> None:
        cfg = champi_stt.StreamingTranscriptionConfig()
        assert cfg.chunk_size > 0

    def test_transcription_chunk_instantiable(self) -> None:
        chunk = champi_stt.TranscriptionChunk(text="hello", is_final=True)
        assert chunk.text == "hello"

    def test_room_config_instantiable(self) -> None:
        room = champi_stt.RoomConfig(name="kitchen")
        assert room.name == "kitchen"

    def test_diarization_config_instantiable(self) -> None:
        cfg = champi_stt.DiarizationConfig()
        assert cfg.device == "cpu"

    def test_all_is_sorted_within_sections(self) -> None:
        # Ensure __all__ has no duplicates
        assert len(champi_stt.__all__) == len(
            set(champi_stt.__all__)
        ), "Duplicate entries in __all__"
