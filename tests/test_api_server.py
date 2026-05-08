"""Tests for the REST API server."""

from __future__ import annotations

import asyncio
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_provider():
    prov = MagicMock()
    prov.__class__.__name__ = "MockProvider"
    prov.is_loaded = True
    prov.transcribe = AsyncMock(return_value="hello world")
    return prov


class TestCreateApiApp:
    def test_raises_without_fastapi(self) -> None:
        with patch("champi_stt.api.server.FASTAPI_AVAILABLE", False):
            from champi_stt.api.server import create_api_app

            with pytest.raises(ImportError, match="fastapi"):
                create_api_app()

    def test_status_no_provider(self) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.api.server import create_api_app

        client = TestClient(create_api_app())
        r = client.get("/status")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["provider"] is None
        assert data["ready"] is False

    def test_status_with_provider(self, mock_provider) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.api.server import create_api_app

        client = TestClient(create_api_app(provider=mock_provider))
        r = client.get("/status")
        assert r.status_code == 200
        data = r.json()
        assert data["ready"] is True
        assert data["provider"] == "MockProvider"

    def test_transcribe_no_provider(self) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.api.server import create_api_app

        client = TestClient(create_api_app())
        r = client.post("/transcribe", files={"file": ("audio.wav", b"\x00" * 100, "audio/wav")})
        assert r.status_code == 503

    def test_transcribe_with_provider(self, mock_provider) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.api.server import create_api_app

        client = TestClient(create_api_app(provider=mock_provider))
        r = client.post("/transcribe", files={"file": ("audio.wav", b"\x00" * 100, "audio/wav")})
        assert r.status_code == 200
        data = r.json()
        assert data["text"] == "hello world"
        assert "processing_time" in data

    def test_transcribe_provider_error(self, mock_provider) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.api.server import create_api_app

        mock_provider.transcribe.side_effect = RuntimeError("model exploded")
        client = TestClient(create_api_app(provider=mock_provider))
        r = client.post("/transcribe", files={"file": ("a.wav", b"\x00" * 10, "audio/wav")})
        assert r.status_code == 500

    def test_command_no_queue(self) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.api.server import create_api_app

        client = TestClient(create_api_app())
        r = client.post("/command", json={"text": "play music"})
        assert r.status_code == 503

    def test_command_queued(self) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.api.server import create_api_app

        q: asyncio.Queue[str] = asyncio.Queue()
        client = TestClient(create_api_app(command_queue=q))
        r = client.post("/command", json={"text": "play music"})
        assert r.status_code == 200
        assert r.json()["status"] == "queued"
        assert not q.empty()

    def test_command_empty_text(self) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.api.server import create_api_app

        q: asyncio.Queue[str] = asyncio.Queue()
        client = TestClient(create_api_app(command_queue=q))
        r = client.post("/command", json={"text": "  "})
        assert r.status_code == 400

    def test_docs_endpoint_available(self) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.api.server import create_api_app

        client = TestClient(create_api_app())
        r = client.get("/docs")
        assert r.status_code == 200


class TestServeApi:
    def test_raises_without_fastapi(self) -> None:
        with patch("champi_stt.api.server.FASTAPI_AVAILABLE", False):
            from champi_stt.api.server import serve_api

            with pytest.raises(ImportError):
                serve_api()

    def test_calls_uvicorn(self) -> None:
        pytest.importorskip("fastapi")
        with patch("champi_stt.api.server.uvicorn") as mock_uv:
            from champi_stt.api.server import serve_api

            serve_api(host="0.0.0.0", port=9001)
            mock_uv.run.assert_called_once()
            _, kwargs = mock_uv.run.call_args
            assert kwargs["host"] == "0.0.0.0"
            assert kwargs["port"] == 9001
