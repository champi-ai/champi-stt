"""Tests for the web configuration server."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    cfg = tmp_path / "assistant_config.yaml"
    cfg.write_text(yaml.dump({"llm": {"model": "gpt-4o"}, "stt": {"provider": "whisperlive"}}))
    return cfg


@pytest.fixture
def empty_config_file(tmp_path: Path) -> Path:
    return tmp_path / "nonexistent.yaml"


class TestLoadSaveYaml:
    def test_load_existing(self, config_file: Path) -> None:
        from champi_stt.assistant.web.server import _load_yaml

        data = _load_yaml(config_file)
        assert data["stt"]["provider"] == "whisperlive"

    def test_load_missing_returns_empty(self, empty_config_file: Path) -> None:
        from champi_stt.assistant.web.server import _load_yaml

        assert _load_yaml(empty_config_file) == {}

    def test_save_creates_parents(self, tmp_path: Path) -> None:
        from champi_stt.assistant.web.server import _save_yaml

        target = tmp_path / "sub" / "dir" / "config.yaml"
        _save_yaml(target, {"key": "value"})
        assert target.exists()
        loaded = yaml.safe_load(target.read_text())
        assert loaded["key"] == "value"

    def test_save_overwrites(self, config_file: Path) -> None:
        from champi_stt.assistant.web.server import _save_yaml, _load_yaml

        _save_yaml(config_file, {"new": "data"})
        assert _load_yaml(config_file) == {"new": "data"}


class TestBuildHtml:
    def test_contains_config_json(self) -> None:
        from champi_stt.assistant.web.server import _build_html

        html = _build_html('{"key": "val"}')
        assert '{"key": "val"}' in html

    def test_contains_save_function(self) -> None:
        from champi_stt.assistant.web.server import _build_html

        html = _build_html("{}")
        assert "function save()" in html
        assert "function reload()" in html

    def test_html_structure(self) -> None:
        from champi_stt.assistant.web.server import _build_html

        html = _build_html("{}")
        assert "<!DOCTYPE html>" in html
        assert "<textarea" in html


class TestCreateApp:
    def test_raises_without_fastapi(self, config_file: Path) -> None:
        with patch("champi_stt.assistant.web.server.FASTAPI_AVAILABLE", False):
            from champi_stt.assistant.web.server import create_app

            with pytest.raises(ImportError, match="fastapi"):
                create_app(config_file)

    def test_get_index(self, config_file: Path) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.assistant.web.server import create_app

        client = TestClient(create_app(config_file))
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_get_config(self, config_file: Path) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.assistant.web.server import create_app

        client = TestClient(create_app(config_file))
        r = client.get("/config")
        assert r.status_code == 200
        data = r.json()
        assert data["stt"]["provider"] == "whisperlive"

    def test_post_config_saves(self, config_file: Path) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.assistant.web.server import create_app

        client = TestClient(create_app(config_file))
        r = client.post("/config", json={"stt": {"provider": "deepgram"}})
        assert r.status_code == 200
        assert r.json()["status"] == "saved"
        loaded = yaml.safe_load(config_file.read_text())
        assert loaded["stt"]["provider"] == "deepgram"

    def test_post_config_reload_triggers_callback(self, config_file: Path) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.assistant.web.server import create_app

        callback = MagicMock()
        client = TestClient(create_app(config_file, reload_callback=callback))
        r = client.post("/config/reload", json={"stt": {"provider": "deepgram"}})
        assert r.status_code == 200
        assert r.json()["reload"] is True
        callback.assert_called_once()

    def test_post_config_reload_no_callback(self, config_file: Path) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.assistant.web.server import create_app

        client = TestClient(create_app(config_file))
        r = client.post("/config/reload", json={"key": "v"})
        assert r.status_code == 200
        assert r.json()["reload"] is False

    def test_get_index_missing_config(self, empty_config_file: Path) -> None:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from champi_stt.assistant.web.server import create_app

        client = TestClient(create_app(empty_config_file))
        r = client.get("/")
        assert r.status_code == 200


class TestServe:
    def test_raises_without_fastapi(self, config_file: Path) -> None:
        with patch("champi_stt.assistant.web.server.FASTAPI_AVAILABLE", False):
            from champi_stt.assistant.web.server import serve

            with pytest.raises(ImportError):
                serve(config_file)

    def test_calls_uvicorn_run(self, config_file: Path) -> None:
        pytest.importorskip("fastapi")
        with patch("champi_stt.assistant.web.server.uvicorn") as mock_uvicorn:
            from champi_stt.assistant.web.server import serve

            serve(config_file, host="127.0.0.1", port=9000)
            mock_uvicorn.run.assert_called_once()
            _, kwargs = mock_uvicorn.run.call_args
            assert kwargs["host"] == "127.0.0.1"
            assert kwargs["port"] == 9000
