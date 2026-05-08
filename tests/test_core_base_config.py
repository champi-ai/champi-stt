"""Tests for base STT config."""

import os
from dataclasses import dataclass
from typing import ClassVar

import pytest

from champi_stt.core.base_config import BaseSTTConfig


@dataclass
class ConcreteConfig(BaseSTTConfig):
    extra: str = "default"

    @classmethod
    def from_env(cls) -> "ConcreteConfig":
        return cls(extra=os.environ.get("EXTRA", "default"))


class TestBaseSTTConfig:
    def test_defaults(self):
        cfg = ConcreteConfig()
        assert cfg.language is None
        assert cfg.task == "transcribe"
        assert cfg.sample_rate == 16000
        assert cfg.save_transcriptions is False

    def test_to_dict(self):
        cfg = ConcreteConfig(language="en", extra="x")
        d = cfg.to_dict()
        assert d["language"] == "en"
        assert d["extra"] == "x"
        assert d["task"] == "transcribe"

    def test_from_dict(self):
        cfg = ConcreteConfig.from_dict({"language": "fr", "extra": "y", "unknown_key": "ignored"})
        assert cfg.language == "fr"
        assert cfg.extra == "y"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("EXTRA", "env_val")
        cfg = ConcreteConfig.from_env()
        assert cfg.extra == "env_val"

    def test_validate_directories_creates_cache(self, tmp_path):
        cfg = ConcreteConfig(cache_dir=str(tmp_path / "cache"))
        cfg.validate_directories()
        assert os.path.isdir(cfg.cache_dir)

    def test_validate_directories_creates_transcriptions(self, tmp_path):
        cfg = ConcreteConfig(
            cache_dir=str(tmp_path / "cache"),
            save_transcriptions=True,
            transcriptions_dir=str(tmp_path / "trans"),
        )
        cfg.validate_directories()
        assert os.path.isdir(cfg.transcriptions_dir)

    def test_validate_directories_skip_transcriptions_when_disabled(self, tmp_path):
        cfg = ConcreteConfig(
            cache_dir=str(tmp_path / "cache"),
            save_transcriptions=False,
            transcriptions_dir=str(tmp_path / "trans"),
        )
        cfg.validate_directories()
        assert not os.path.exists(str(tmp_path / "trans"))
