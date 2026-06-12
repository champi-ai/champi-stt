"""Unit tests and JSON schema validation for the four MCP tools.

Covers all four tools registered by ``create_mcp_server()``:
- ``list_providers``
- ``get_provider_status``
- ``transcribe_audio``
- ``detect_language``

All tests mock the underlying provider so no audio hardware is required.
Tests that would need real GPU or microphone access are skipped explicitly.
"""

from __future__ import annotations

import tempfile
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_provider(
    *,
    model_info: dict | None = None,
    transcribe_result: str | dict = "hello world",
    detect_result: tuple = ("en", 0.99, []),
    initialize_raises: Exception | None = None,
    transcribe_raises: Exception | None = None,
    detect_raises: Exception | None = None,
) -> MagicMock:
    """Build a mock STT provider with configurable return values and errors."""
    prov = MagicMock()
    prov.initialize = AsyncMock(side_effect=initialize_raises)
    prov.shutdown = AsyncMock()
    prov.transcribe = AsyncMock(
        side_effect=transcribe_raises, return_value=transcribe_result
    )
    prov.detect_language = AsyncMock(
        side_effect=detect_raises, return_value=detect_result
    )
    prov.get_model_info = AsyncMock(
        return_value=model_info or {"status": "loaded", "provider": "mock"}
    )
    return prov


def _raw(call_tool_result: tuple) -> dict:
    """Extract the structured result dict from a FastMCP ``call_tool`` response."""
    return call_tool_result[1]


@pytest.fixture()
def server() -> Any:
    """Fresh FastMCP server instance per test (factory pattern)."""
    from champi_stt.mcp.server import create_mcp_server

    return create_mcp_server()


def _schema(server: Any, tool_name: str) -> dict:
    """Return the JSON Schema parameters dict for a named tool."""
    return server._tool_manager._tools[tool_name].parameters


# ---------------------------------------------------------------------------
# JSON Schema: list_providers
# ---------------------------------------------------------------------------


class TestListProvidersSchema:
    """The list_providers tool takes no parameters."""

    def test_schema_type_is_object(self, server: Any) -> None:
        assert _schema(server, "list_providers")["type"] == "object"

    def test_schema_has_no_required_params(self, server: Any) -> None:
        schema = _schema(server, "list_providers")
        required = schema.get("required", [])
        assert required == []

    def test_schema_properties_is_empty(self, server: Any) -> None:
        schema = _schema(server, "list_providers")
        assert schema.get("properties") == {}


# ---------------------------------------------------------------------------
# JSON Schema: get_provider_status
# ---------------------------------------------------------------------------


class TestGetProviderStatusSchema:
    """get_provider_status requires a single string ``provider`` parameter."""

    def test_schema_type_is_object(self, server: Any) -> None:
        assert _schema(server, "get_provider_status")["type"] == "object"

    def test_provider_param_is_required(self, server: Any) -> None:
        schema = _schema(server, "get_provider_status")
        assert "provider" in schema.get("required", [])

    def test_provider_param_type_is_string(self, server: Any) -> None:
        schema = _schema(server, "get_provider_status")
        assert schema["properties"]["provider"]["type"] == "string"

    def test_only_provider_is_required(self, server: Any) -> None:
        schema = _schema(server, "get_provider_status")
        assert schema.get("required") == ["provider"]


# ---------------------------------------------------------------------------
# JSON Schema: transcribe_audio
# ---------------------------------------------------------------------------


class TestTranscribeAudioSchema:
    """transcribe_audio: required ``audio_path: string``; optional ``language`` and ``provider`` (string | null)."""

    def test_schema_type_is_object(self, server: Any) -> None:
        assert _schema(server, "transcribe_audio")["type"] == "object"

    def test_audio_path_is_required(self, server: Any) -> None:
        schema = _schema(server, "transcribe_audio")
        assert "audio_path" in schema.get("required", [])

    def test_only_audio_path_is_required(self, server: Any) -> None:
        schema = _schema(server, "transcribe_audio")
        assert schema.get("required") == ["audio_path"]

    def test_audio_path_type_is_string(self, server: Any) -> None:
        schema = _schema(server, "transcribe_audio")
        assert schema["properties"]["audio_path"]["type"] == "string"

    def test_language_accepts_string(self, server: Any) -> None:
        schema = _schema(server, "transcribe_audio")
        any_of_types = {
            e["type"] for e in schema["properties"]["language"].get("anyOf", [])
        }
        assert "string" in any_of_types

    def test_language_accepts_null(self, server: Any) -> None:
        schema = _schema(server, "transcribe_audio")
        any_of_types = {
            e["type"] for e in schema["properties"]["language"].get("anyOf", [])
        }
        assert "null" in any_of_types

    def test_language_default_is_none(self, server: Any) -> None:
        schema = _schema(server, "transcribe_audio")
        assert schema["properties"]["language"]["default"] is None

    def test_provider_accepts_string(self, server: Any) -> None:
        schema = _schema(server, "transcribe_audio")
        any_of_types = {
            e["type"] for e in schema["properties"]["provider"].get("anyOf", [])
        }
        assert "string" in any_of_types

    def test_provider_accepts_null(self, server: Any) -> None:
        schema = _schema(server, "transcribe_audio")
        any_of_types = {
            e["type"] for e in schema["properties"]["provider"].get("anyOf", [])
        }
        assert "null" in any_of_types

    def test_provider_default_is_none(self, server: Any) -> None:
        schema = _schema(server, "transcribe_audio")
        assert schema["properties"]["provider"]["default"] is None


# ---------------------------------------------------------------------------
# JSON Schema: detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguageSchema:
    """detect_language: required ``audio_path: string``; optional ``provider`` (string | null)."""

    def test_schema_type_is_object(self, server: Any) -> None:
        assert _schema(server, "detect_language")["type"] == "object"

    def test_audio_path_is_required(self, server: Any) -> None:
        schema = _schema(server, "detect_language")
        assert "audio_path" in schema.get("required", [])

    def test_only_audio_path_is_required(self, server: Any) -> None:
        schema = _schema(server, "detect_language")
        assert schema.get("required") == ["audio_path"]

    def test_audio_path_type_is_string(self, server: Any) -> None:
        schema = _schema(server, "detect_language")
        assert schema["properties"]["audio_path"]["type"] == "string"

    def test_provider_accepts_string(self, server: Any) -> None:
        schema = _schema(server, "detect_language")
        any_of_types = {
            e["type"] for e in schema["properties"]["provider"].get("anyOf", [])
        }
        assert "string" in any_of_types

    def test_provider_accepts_null(self, server: Any) -> None:
        schema = _schema(server, "detect_language")
        any_of_types = {
            e["type"] for e in schema["properties"]["provider"].get("anyOf", [])
        }
        assert "null" in any_of_types

    def test_provider_default_is_none(self, server: Any) -> None:
        schema = _schema(server, "detect_language")
        assert schema["properties"]["provider"]["default"] is None


# ---------------------------------------------------------------------------
# Tool: list_providers
# ---------------------------------------------------------------------------


class TestListProvidersTool:
    @pytest.mark.asyncio
    async def test_returns_list_of_strings(self, server: Any) -> None:
        result = _raw(await server.call_tool("list_providers", {}))
        assert isinstance(result["result"], list)
        assert all(isinstance(p, str) for p in result["result"])

    @pytest.mark.asyncio
    async def test_result_is_nonempty(self, server: Any) -> None:
        result = _raw(await server.call_tool("list_providers", {}))
        assert len(result["result"]) > 0

    @pytest.mark.asyncio
    async def test_contains_whisperlive(self, server: Any) -> None:
        result = _raw(await server.call_tool("list_providers", {}))
        assert "whisperlive" in result["result"]

    @pytest.mark.asyncio
    async def test_contains_openai_whisper(self, server: Any) -> None:
        result = _raw(await server.call_tool("list_providers", {}))
        assert "openai_whisper" in result["result"]


# ---------------------------------------------------------------------------
# Tool: get_provider_status
# ---------------------------------------------------------------------------


class TestGetProviderStatusTool:
    @pytest.mark.asyncio
    async def test_returns_model_info_dict(self, server: Any) -> None:
        prov = _make_provider(model_info={"status": "loaded", "model": "base"})
        with patch("champi_stt.get_provider", return_value=prov):
            result = _raw(
                await server.call_tool(
                    "get_provider_status", {"provider": "whisperlive"}
                )
            )
        assert result["status"] == "loaded"

    @pytest.mark.asyncio
    async def test_get_model_info_is_awaited(self, server: Any) -> None:
        prov = _make_provider()
        with patch("champi_stt.get_provider", return_value=prov):
            await server.call_tool("get_provider_status", {"provider": "whisperlive"})
        prov.get_model_info.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_provider_returns_error_dict(self, server: Any) -> None:
        with patch("champi_stt.get_provider", side_effect=ValueError("unknown")):
            result = _raw(
                await server.call_tool(
                    "get_provider_status", {"provider": "nonexistent"}
                )
            )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_error_dict_contains_provider_name(self, server: Any) -> None:
        with patch("champi_stt.get_provider", side_effect=ValueError("bad")):
            result = _raw(
                await server.call_tool(
                    "get_provider_status", {"provider": "nonexistent"}
                )
            )
        assert result["provider"] == "nonexistent"

    @pytest.mark.asyncio
    async def test_error_dict_contains_error_type(self, server: Any) -> None:
        with patch("champi_stt.get_provider", side_effect=ValueError("bad")):
            result = _raw(
                await server.call_tool(
                    "get_provider_status", {"provider": "nonexistent"}
                )
            )
        assert result["error_type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_error_dict_contains_error_message(self, server: Any) -> None:
        with patch("champi_stt.get_provider", side_effect=ValueError("bad input")):
            result = _raw(
                await server.call_tool(
                    "get_provider_status", {"provider": "nonexistent"}
                )
            )
        assert "bad input" in result["error_message"]


# ---------------------------------------------------------------------------
# Tool: transcribe_audio
# ---------------------------------------------------------------------------


class TestTranscribeAudioTool:
    @pytest.mark.asyncio
    async def test_missing_file_returns_error_string(self, server: Any) -> None:
        result = _raw(
            await server.call_tool(
                "transcribe_audio", {"audio_path": "/no/such/file.wav"}
            )
        )
        assert "error" in result["result"].lower()

    @pytest.mark.asyncio
    async def test_transcribes_existing_file(self, server: Any) -> None:
        prov = _make_provider(transcribe_result="hello world")
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov),
        ):
            result = _raw(
                await server.call_tool("transcribe_audio", {"audio_path": f.name})
            )
        assert result["result"] == "hello world"

    @pytest.mark.asyncio
    async def test_dict_result_extracts_text_field(self, server: Any) -> None:
        prov = _make_provider(
            transcribe_result={"text": "extracted text", "confidence": 0.9}
        )
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov),
        ):
            result = _raw(
                await server.call_tool("transcribe_audio", {"audio_path": f.name})
            )
        assert result["result"] == "extracted text"

    @pytest.mark.asyncio
    async def test_provider_exception_returns_error_string(self, server: Any) -> None:
        prov = _make_provider(transcribe_raises=RuntimeError("GPU unavailable"))
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov),
        ):
            result = _raw(
                await server.call_tool("transcribe_audio", {"audio_path": f.name})
            )
        assert "error" in result["result"].lower()
        assert "GPU unavailable" in result["result"]

    @pytest.mark.asyncio
    async def test_language_hint_passed_to_provider(self, server: Any) -> None:
        prov = _make_provider()
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov),
        ):
            await server.call_tool(
                "transcribe_audio", {"audio_path": f.name, "language": "fr"}
            )
        _, kwargs = prov.transcribe.call_args
        assert kwargs.get("language") == "fr"

    @pytest.mark.asyncio
    async def test_provider_initialized_only_once(self, server: Any) -> None:
        prov = _make_provider(transcribe_result="ok")
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov),
        ):
            await server.call_tool("transcribe_audio", {"audio_path": f.name})
            await server.call_tool("transcribe_audio", {"audio_path": f.name})
        prov.initialize.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_env_var_selects_provider(
        self, server: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHAMPI_STT_PROVIDER", "openai_whisper")
        prov = _make_provider()
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov) as mock_get,
        ):
            await server.call_tool("transcribe_audio", {"audio_path": f.name})
        mock_get.assert_called_with("openai_whisper")

    @pytest.mark.asyncio
    async def test_explicit_provider_overrides_env_var(
        self, server: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHAMPI_STT_PROVIDER", "openai_whisper")
        prov = _make_provider()
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov) as mock_get,
        ):
            await server.call_tool(
                "transcribe_audio",
                {"audio_path": f.name, "provider": "whisperlive"},
            )
        mock_get.assert_called_with("whisperlive")


# ---------------------------------------------------------------------------
# Tool: detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguageTool:
    @pytest.mark.asyncio
    async def test_missing_file_returns_error_dict(self, server: Any) -> None:
        result = _raw(
            await server.call_tool(
                "detect_language", {"audio_path": "/no/such/file.wav"}
            )
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_missing_file_error_type_is_file_not_found(self, server: Any) -> None:
        result = _raw(
            await server.call_tool(
                "detect_language", {"audio_path": "/no/such/file.wav"}
            )
        )
        assert result["error_type"] == "FileNotFoundError"

    @pytest.mark.asyncio
    async def test_missing_file_error_message_contains_path(self, server: Any) -> None:
        result = _raw(
            await server.call_tool(
                "detect_language", {"audio_path": "/no/such/file.wav"}
            )
        )
        assert "/no/such/file.wav" in result["error_message"]

    @pytest.mark.asyncio
    async def test_returns_language_code(self, server: Any) -> None:
        prov = _make_provider(detect_result=("fr", 0.87, []))
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov),
        ):
            result = _raw(
                await server.call_tool("detect_language", {"audio_path": f.name})
            )
        assert result["language"] == "fr"

    @pytest.mark.asyncio
    async def test_returns_probability(self, server: Any) -> None:
        prov = _make_provider(detect_result=("es", 0.75, []))
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov),
        ):
            result = _raw(
                await server.call_tool("detect_language", {"audio_path": f.name})
            )
        assert result["probability"] == pytest.approx(0.75)

    @pytest.mark.asyncio
    async def test_provider_exception_returns_error_dict(self, server: Any) -> None:
        prov = _make_provider(detect_raises=RuntimeError("model not loaded"))
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov),
        ):
            result = _raw(
                await server.call_tool("detect_language", {"audio_path": f.name})
            )
        assert result["error"] is True
        assert result["error_type"] == "RuntimeError"

    @pytest.mark.asyncio
    async def test_env_var_selects_provider(
        self, server: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHAMPI_STT_PROVIDER", "openai_whisper")
        prov = _make_provider()
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov) as mock_get,
        ):
            await server.call_tool("detect_language", {"audio_path": f.name})
        mock_get.assert_called_with("openai_whisper")

    @pytest.mark.asyncio
    async def test_explicit_provider_overrides_env_var(
        self, server: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHAMPI_STT_PROVIDER", "openai_whisper")
        prov = _make_provider()
        with (
            tempfile.NamedTemporaryFile(suffix=".wav") as f,
            patch("champi_stt.get_provider", return_value=prov) as mock_get,
        ):
            await server.call_tool(
                "detect_language",
                {"audio_path": f.name, "provider": "whisperlive"},
            )
        mock_get.assert_called_with("whisperlive")
