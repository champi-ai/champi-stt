"""Tests for launchd plist installer."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from champi_stt.assistant.service.launchd.installer import (
    _PLIST_FILENAME,
    _PLIST_LABEL,
    _champi_exec,
    _default_config_path,
    _launch_agents_dir,
    install,
    is_installed,
    is_loaded,
    status,
    uninstall,
)


@pytest.fixture
def fake_launchd(tmp_path):
    agents_dir = tmp_path / "Library" / "LaunchAgents"
    agents_dir.mkdir(parents=True)
    log_dir = tmp_path / "Library" / "Logs" / "champi-stt"

    with patch("champi_stt.assistant.service.launchd.installer.shutil.which", return_value="/usr/bin/launchctl"):
        with patch("champi_stt.assistant.service.launchd.installer._launch_agents_dir", return_value=agents_dir):
            with patch("champi_stt.assistant.service.launchd.installer._log_dir", return_value=str(log_dir)):
                with patch("champi_stt.assistant.service.launchd.installer.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                    yield agents_dir, mock_run


class TestInstall:
    def test_creates_plist_file(self, fake_launchd):
        agents_dir, _ = fake_launchd
        path = install(config="/fake/config.yaml", load=False)
        assert (agents_dir / _PLIST_FILENAME).exists()
        assert path == agents_dir / _PLIST_FILENAME

    def test_plist_content(self, fake_launchd):
        agents_dir, _ = fake_launchd
        install(config="/fake/config.yaml", load=False)
        content = (agents_dir / _PLIST_FILENAME).read_text()
        assert "/fake/config.yaml" in content
        assert _PLIST_LABEL in content
        assert "<key>RunAtLoad</key>" in content
        assert "<key>KeepAlive</key>" in content
        assert "ProgramArguments" in content

    def test_launchctl_load_called(self, fake_launchd):
        _, mock_run = fake_launchd
        install(config="/cfg.yaml", load=True)
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("load" in c for c in calls)

    def test_no_load(self, fake_launchd):
        _, mock_run = fake_launchd
        install(config="/cfg.yaml", load=False)
        calls = [str(c) for c in mock_run.call_args_list]
        assert not any("'load'" in c for c in calls)

    def test_raises_without_launchctl(self, tmp_path):
        with patch("champi_stt.assistant.service.launchd.installer.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="launchctl not found"):
                install()

    def test_creates_log_dir(self, fake_launchd, tmp_path):
        agents_dir, _ = fake_launchd
        log_path = tmp_path / "new_logs"
        with patch("champi_stt.assistant.service.launchd.installer._log_dir", return_value=str(log_path)):
            install(config="/cfg.yaml", load=False)
        assert log_path.exists()


class TestUninstall:
    def test_removes_plist_file(self, fake_launchd):
        agents_dir, _ = fake_launchd
        (agents_dir / _PLIST_FILENAME).write_text("<plist/>")
        uninstall()
        assert not (agents_dir / _PLIST_FILENAME).exists()

    def test_launchctl_unload_called(self, fake_launchd):
        agents_dir, mock_run = fake_launchd
        (agents_dir / _PLIST_FILENAME).write_text("<plist/>")
        uninstall(unload=True)
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("unload" in c for c in calls)

    def test_missing_file_ok(self, fake_launchd):
        uninstall()  # should not raise


class TestStatus:
    def test_returns_output(self, fake_launchd):
        _, mock_run = fake_launchd
        mock_run.return_value = MagicMock(stdout="PID\t0\tai.champi.stt\n", stderr="")
        result = status()
        assert isinstance(result, str)

    def test_no_launchctl(self):
        with patch("champi_stt.assistant.service.launchd.installer.shutil.which", return_value=None):
            result = status()
            assert "not available" in result


class TestIsInstalled:
    def test_true_when_file_exists(self, fake_launchd):
        agents_dir, _ = fake_launchd
        (agents_dir / _PLIST_FILENAME).write_text("<plist/>")
        assert is_installed() is True

    def test_false_when_missing(self, fake_launchd):
        assert is_installed() is False


class TestIsLoaded:
    def test_loaded(self, fake_launchd):
        _, mock_run = fake_launchd
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        assert is_loaded() is True

    def test_not_loaded(self, fake_launchd):
        _, mock_run = fake_launchd
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
        assert is_loaded() is False

    def test_no_launchctl(self):
        with patch("champi_stt.assistant.service.launchd.installer.shutil.which", return_value=None):
            assert is_loaded() is False


class TestHelpers:
    def test_default_config_path(self):
        path = _default_config_path()
        assert "champi-stt" in path
        assert path.endswith(".yaml")

    def test_champi_exec_returns_string(self):
        result = _champi_exec()
        assert isinstance(result, str)
        assert len(result) > 0
