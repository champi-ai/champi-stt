"""Tests for systemd service installer."""

from unittest.mock import MagicMock, patch

import pytest

from champi_stt.assistant.service.systemd.installer import (
    _SERVICE_NAME,
    _champi_exec,
    _default_config_path,
    install,
    is_active,
    is_installed,
    status,
    uninstall,
)


@pytest.fixture
def fake_systemd(tmp_path):
    """Patch systemctl availability and service dir to use tmp_path."""
    service_dir = tmp_path / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True)

    with (
        patch(
            "champi_stt.assistant.service.systemd.installer.shutil.which",
            return_value="/bin/systemctl",
        ),
        patch(
            "champi_stt.assistant.service.systemd.installer._systemd_user_dir",
            return_value=service_dir,
        ),
        patch(
            "champi_stt.assistant.service.systemd.installer.subprocess.run"
        ) as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="active\n", stderr="")
        yield service_dir, mock_run


class TestInstall:
    def test_creates_service_file(self, fake_systemd):
        service_dir, _ = fake_systemd
        path = install(config="/fake/config.yaml", enable=False, start=False)
        assert (service_dir / _SERVICE_NAME).exists()
        assert path == service_dir / _SERVICE_NAME

    def test_service_file_content(self, fake_systemd):
        service_dir, _ = fake_systemd
        install(config="/fake/config.yaml", enable=False, start=False)
        content = (service_dir / _SERVICE_NAME).read_text()
        assert "/fake/config.yaml" in content
        assert "[Unit]" in content
        assert "[Service]" in content
        assert "[Install]" in content
        assert "ExecStart=" in content

    def test_daemon_reload_called(self, fake_systemd):
        _, mock_run = fake_systemd
        install(config="/cfg.yaml", enable=False, start=False)
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("daemon-reload" in c for c in calls)

    def test_enable_called_when_requested(self, fake_systemd):
        _, mock_run = fake_systemd
        install(config="/cfg.yaml", enable=True, start=False)
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("enable" in c for c in calls)

    def test_start_called_when_requested(self, fake_systemd):
        _, mock_run = fake_systemd
        install(config="/cfg.yaml", enable=False, start=True)
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("start" in c for c in calls)

    def test_no_enable_no_start(self, fake_systemd):
        _, mock_run = fake_systemd
        install(config="/cfg.yaml", enable=False, start=False)
        calls = [str(c) for c in mock_run.call_args_list]
        assert not any("enable" in c for c in calls)
        assert not any('"start"' in c for c in calls)

    def test_raises_without_systemctl(self, tmp_path):
        with (
            patch(
                "champi_stt.assistant.service.systemd.installer.shutil.which",
                return_value=None,
            ),
            pytest.raises(RuntimeError, match="systemctl not found"),
        ):
            install()


class TestUninstall:
    def test_removes_service_file(self, fake_systemd):
        service_dir, _ = fake_systemd
        service_file = service_dir / _SERVICE_NAME
        service_file.write_text("[Unit]\n")
        uninstall()
        assert not service_file.exists()

    def test_stop_and_disable_called(self, fake_systemd):
        service_dir, mock_run = fake_systemd
        (service_dir / _SERVICE_NAME).write_text("[Unit]\n")
        uninstall(stop=True)
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("stop" in c for c in calls)
        assert any("disable" in c for c in calls)

    def test_missing_file_ok(self, fake_systemd):
        # Should not raise even if file doesn't exist
        uninstall()


class TestStatus:
    def test_returns_output(self, fake_systemd):
        _, mock_run = fake_systemd
        mock_run.return_value = MagicMock(stdout="active running\n", stderr="")
        result = status()
        assert isinstance(result, str)

    def test_no_systemctl(self):
        with patch(
            "champi_stt.assistant.service.systemd.installer.shutil.which",
            return_value=None,
        ):
            result = status()
            assert "not available" in result


class TestIsInstalled:
    def test_true_when_file_exists(self, fake_systemd):
        service_dir, _ = fake_systemd
        (service_dir / _SERVICE_NAME).write_text("[Unit]\n")
        assert is_installed() is True

    def test_false_when_missing(self, fake_systemd):
        assert is_installed() is False


class TestIsActive:
    def test_active(self, fake_systemd):
        _, mock_run = fake_systemd
        mock_run.return_value = MagicMock(stdout="active\n", stderr="", returncode=0)
        assert is_active() is True

    def test_inactive(self, fake_systemd):
        _, mock_run = fake_systemd
        mock_run.return_value = MagicMock(stdout="inactive\n", stderr="", returncode=3)
        assert is_active() is False

    def test_no_systemctl(self):
        with patch(
            "champi_stt.assistant.service.systemd.installer.shutil.which",
            return_value=None,
        ):
            assert is_active() is False


class TestHelpers:
    def test_default_config_path_in_home(self):
        path = _default_config_path()
        assert "champi-stt" in path
        assert path.endswith(".yaml")

    def test_champi_exec_returns_string(self):
        result = _champi_exec()
        assert isinstance(result, str)
        assert len(result) > 0
