"""Regression tests for hardcoded dev-path bugs (Phase 1 fix).

These guard against any future re-introduction of developer-machine
specific paths (mcp-champi, /mnt/raid_0_drive) into the source tree or
default config values.
"""

import pathlib


def test_whisperlive_cache_dir_default_uses_champi_stt():
    from champi_stt.providers.whisperlive.config import WhisperLiveConfig

    cfg = WhisperLiveConfig()
    assert "champi-stt" in cfg.cache_dir
    assert "/mnt/raid_0_drive" not in cfg.cache_dir
    assert "mcp-champi" not in cfg.cache_dir
    assert "mcp_champi" not in cfg.cache_dir


def test_whisperlive_transcriptions_dir_default_uses_champi_stt():
    from champi_stt.providers.whisperlive.config import WhisperLiveConfig

    cfg = WhisperLiveConfig()
    assert "champi-stt" in cfg.transcriptions_dir
    assert "mcp-champi" not in cfg.transcriptions_dir


def test_no_source_file_contains_mcp_champi_paths():
    src = pathlib.Path("src/champi_stt")
    banned = ["/mnt/raid_0_drive", "mcp-champi", "mcp_champi"]
    for py_file in src.rglob("*.py"):
        text = py_file.read_text()
        for bad in banned:
            assert bad not in text, f"{py_file} still contains '{bad}'"
