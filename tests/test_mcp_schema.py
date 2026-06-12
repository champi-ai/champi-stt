"""JSON schema contract tests for MCP tool parameter schemas.

These tests verify the parameter schema of each registered MCP tool is
correct and stable.  Behaviour is covered by ``test_mcp_server.py``; this
file covers the contract only.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def tools() -> dict:
    """Return the ``_tools`` registry from a freshly created MCP server."""
    from champi_stt.mcp.server import create_mcp_server

    srv = create_mcp_server()
    return srv._tool_manager._tools


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _schema(tools: dict, name: str) -> dict:
    """Return the ``parameters`` dict for the named tool."""
    return tools[name].parameters


# ---------------------------------------------------------------------------
# transcribe_audio
# ---------------------------------------------------------------------------


class TestTranscribeAudioSchema:
    def test_schema_is_object_type(self, tools: dict) -> None:
        assert _schema(tools, "transcribe_audio")["type"] == "object"

    def test_audio_path_is_required(self, tools: dict) -> None:
        assert "audio_path" in _schema(tools, "transcribe_audio")["required"]

    def test_audio_path_is_string(self, tools: dict) -> None:
        prop = _schema(tools, "transcribe_audio")["properties"]["audio_path"]
        assert prop["type"] == "string"

    def test_language_is_not_required(self, tools: dict) -> None:
        required = _schema(tools, "transcribe_audio").get("required", [])
        assert "language" not in required

    def test_language_accepts_string_or_null(self, tools: dict) -> None:
        prop = _schema(tools, "transcribe_audio")["properties"]["language"]
        types = {item["type"] for item in prop["anyOf"]}
        assert types == {"string", "null"}

    def test_language_defaults_to_null(self, tools: dict) -> None:
        prop = _schema(tools, "transcribe_audio")["properties"]["language"]
        assert prop["default"] is None

    def test_provider_is_not_required(self, tools: dict) -> None:
        required = _schema(tools, "transcribe_audio").get("required", [])
        assert "provider" not in required

    def test_provider_accepts_string_or_null(self, tools: dict) -> None:
        prop = _schema(tools, "transcribe_audio")["properties"]["provider"]
        types = {item["type"] for item in prop["anyOf"]}
        assert types == {"string", "null"}

    def test_provider_defaults_to_null(self, tools: dict) -> None:
        prop = _schema(tools, "transcribe_audio")["properties"]["provider"]
        assert prop["default"] is None

    def test_only_known_properties_present(self, tools: dict) -> None:
        props = set(_schema(tools, "transcribe_audio")["properties"].keys())
        assert props == {"audio_path", "language", "provider"}

    def test_only_audio_path_in_required(self, tools: dict) -> None:
        required = _schema(tools, "transcribe_audio")["required"]
        assert required == ["audio_path"]


# ---------------------------------------------------------------------------
# detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguageSchema:
    def test_schema_is_object_type(self, tools: dict) -> None:
        assert _schema(tools, "detect_language")["type"] == "object"

    def test_audio_path_is_required(self, tools: dict) -> None:
        assert "audio_path" in _schema(tools, "detect_language")["required"]

    def test_audio_path_is_string(self, tools: dict) -> None:
        prop = _schema(tools, "detect_language")["properties"]["audio_path"]
        assert prop["type"] == "string"

    def test_provider_is_not_required(self, tools: dict) -> None:
        required = _schema(tools, "detect_language").get("required", [])
        assert "provider" not in required

    def test_provider_accepts_string_or_null(self, tools: dict) -> None:
        prop = _schema(tools, "detect_language")["properties"]["provider"]
        types = {item["type"] for item in prop["anyOf"]}
        assert types == {"string", "null"}

    def test_provider_defaults_to_null(self, tools: dict) -> None:
        prop = _schema(tools, "detect_language")["properties"]["provider"]
        assert prop["default"] is None

    def test_only_known_properties_present(self, tools: dict) -> None:
        props = set(_schema(tools, "detect_language")["properties"].keys())
        assert props == {"audio_path", "provider"}

    def test_only_audio_path_in_required(self, tools: dict) -> None:
        required = _schema(tools, "detect_language")["required"]
        assert required == ["audio_path"]


# ---------------------------------------------------------------------------
# list_providers
# ---------------------------------------------------------------------------


class TestListProvidersSchema:
    def test_schema_is_object_type(self, tools: dict) -> None:
        assert _schema(tools, "list_providers")["type"] == "object"

    def test_has_no_required_parameters(self, tools: dict) -> None:
        schema = _schema(tools, "list_providers")
        assert schema.get("required", []) == []

    def test_has_no_properties(self, tools: dict) -> None:
        props = _schema(tools, "list_providers").get("properties", {})
        assert props == {}


# ---------------------------------------------------------------------------
# get_provider_status
# ---------------------------------------------------------------------------


class TestGetProviderStatusSchema:
    def test_schema_is_object_type(self, tools: dict) -> None:
        assert _schema(tools, "get_provider_status")["type"] == "object"

    def test_provider_is_required(self, tools: dict) -> None:
        assert "provider" in _schema(tools, "get_provider_status")["required"]

    def test_provider_is_string(self, tools: dict) -> None:
        prop = _schema(tools, "get_provider_status")["properties"]["provider"]
        assert prop["type"] == "string"

    def test_only_provider_in_required(self, tools: dict) -> None:
        required = _schema(tools, "get_provider_status")["required"]
        assert required == ["provider"]

    def test_only_known_properties_present(self, tools: dict) -> None:
        props = set(_schema(tools, "get_provider_status")["properties"].keys())
        assert props == {"provider"}
