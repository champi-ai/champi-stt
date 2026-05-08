"""
Systemd user service installer for champi-stt.

Installs champi-stt as a ~/.config/systemd/user/ service so it starts
automatically on login without requiring root privileges.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from string import Template

from loguru import logger

_SERVICE_TEMPLATE = Template("""\
[Unit]
Description=Champi STT Voice Assistant
After=network.target sound.target
Wants=network.target

[Service]
Type=simple
ExecStart=$exec_path start --config $config_path
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
""")

_SERVICE_NAME = "champi-stt.service"


def _systemd_user_dir() -> Path:
    return Path(os.path.expanduser("~/.config/systemd/user"))


def _champi_exec() -> str:
    """Return the absolute path to the champi-stt executable."""
    exe = shutil.which("champi-stt")
    if exe:
        return exe
    # Fall back to the current Python environment's bin dir
    return str(Path(sys.executable).parent / "champi-stt")


def _default_config_path() -> str:
    return str(Path(os.path.expanduser("~/.config/champi-stt/assistant_config.yaml")))


def install(
    config: str | None = None,
    user: str | None = None,
    enable: bool = True,
    start: bool = True,
) -> Path:
    """
    Install champi-stt as a systemd user service.

    Args:
        config: Path to assistant_config.yaml (defaults to ~/.config/champi-stt/assistant_config.yaml)
        user:   Unused — user services always install to the current user's systemd directory.
        enable: Run `systemctl --user enable` after installing.
        start:  Run `systemctl --user start` after enabling.

    Returns:
        Path to the installed .service file.

    Raises:
        RuntimeError: If systemctl is not available on this system.
    """
    if not shutil.which("systemctl"):
        raise RuntimeError(
            "systemctl not found. Systemd service installation requires a Linux system with systemd."
        )

    config_path = config or _default_config_path()
    exec_path = _champi_exec()

    service_content = _SERVICE_TEMPLATE.substitute(
        exec_path=exec_path,
        config_path=config_path,
    )

    service_dir = _systemd_user_dir()
    service_dir.mkdir(parents=True, exist_ok=True)
    service_file = service_dir / _SERVICE_NAME

    service_file.write_text(service_content)
    logger.info(f"Service file written to: {service_file}")

    # Reload systemd daemon to pick up new unit file
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    logger.info("systemd user daemon reloaded")

    if enable:
        subprocess.run(["systemctl", "--user", "enable", _SERVICE_NAME], check=True)
        logger.info(f"Service enabled: {_SERVICE_NAME}")

    if start:
        subprocess.run(["systemctl", "--user", "start", _SERVICE_NAME], check=True)
        logger.info(f"Service started: {_SERVICE_NAME}")

    return service_file


def uninstall(stop: bool = True) -> None:
    """
    Remove the champi-stt systemd user service.

    Args:
        stop: Stop the service before removing it.
    """
    if shutil.which("systemctl"):
        if stop:
            subprocess.run(
                ["systemctl", "--user", "stop", _SERVICE_NAME],
                check=False,  # don't fail if not running
            )
        subprocess.run(
            ["systemctl", "--user", "disable", _SERVICE_NAME],
            check=False,
        )
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)

    service_file = _systemd_user_dir() / _SERVICE_NAME
    if service_file.exists():
        service_file.unlink()
        logger.info(f"Removed service file: {service_file}")
    else:
        logger.warning(f"Service file not found: {service_file}")


def status() -> str:
    """Return the output of `systemctl --user status champi-stt`."""
    if not shutil.which("systemctl"):
        return "systemctl not available"
    result = subprocess.run(
        ["systemctl", "--user", "status", _SERVICE_NAME],
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr


def is_installed() -> bool:
    """Return True if the service file is present."""
    return (_systemd_user_dir() / _SERVICE_NAME).exists()


def is_active() -> bool:
    """Return True if the service is currently running."""
    if not shutil.which("systemctl"):
        return False
    result = subprocess.run(
        ["systemctl", "--user", "is-active", _SERVICE_NAME],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "active"
