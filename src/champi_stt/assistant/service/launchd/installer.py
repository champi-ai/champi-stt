"""
Launchd plist installer for champi-stt on macOS.

Installs champi-stt as a ~/Library/LaunchAgents/ agent so it starts
automatically on login without requiring root privileges.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from string import Template

from loguru import logger

_PLIST_TEMPLATE = Template("""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.champi.stt</string>

    <key>ProgramArguments</key>
    <array>
        <string>$exec_path</string>
        <string>start</string>
        <string>--config</string>
        <string>$config_path</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>$log_dir/champi-stt.stdout.log</string>

    <key>StandardErrorPath</key>
    <string>$log_dir/champi-stt.stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
</dict>
</plist>
""")

_PLIST_LABEL = "ai.champi.stt"
_PLIST_FILENAME = f"{_PLIST_LABEL}.plist"


def _launch_agents_dir() -> Path:
    return Path(os.path.expanduser("~/Library/LaunchAgents"))


def _log_dir() -> str:
    return str(Path(os.path.expanduser("~/Library/Logs/champi-stt")))


def _champi_exec() -> str:
    exe = shutil.which("champi-stt")
    if exe:
        return exe
    return str(Path(sys.executable).parent / "champi-stt")


def _default_config_path() -> str:
    return str(Path(os.path.expanduser("~/.config/champi-stt/assistant_config.yaml")))


def install(
    config: str | None = None,
    load: bool = True,
) -> Path:
    """
    Install champi-stt as a launchd LaunchAgent.

    Args:
        config: Path to assistant_config.yaml (defaults to ~/.config/champi-stt/assistant_config.yaml)
        load:   Run `launchctl load` after installing.

    Returns:
        Path to the installed .plist file.

    Raises:
        RuntimeError: If launchctl is not available (non-macOS system).
    """
    if not shutil.which("launchctl"):
        raise RuntimeError(
            "launchctl not found. Launchd service installation requires macOS."
        )

    config_path = config or _default_config_path()
    exec_path = _champi_exec()
    log_dir = _log_dir()

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    plist_content = _PLIST_TEMPLATE.substitute(
        exec_path=exec_path,
        config_path=config_path,
        log_dir=log_dir,
    )

    agents_dir = _launch_agents_dir()
    agents_dir.mkdir(parents=True, exist_ok=True)
    plist_file = agents_dir / _PLIST_FILENAME

    plist_file.write_text(plist_content)
    logger.info(f"Plist written to: {plist_file}")

    if load:
        subprocess.run(["launchctl", "load", str(plist_file)], check=True)
        logger.info(f"LaunchAgent loaded: {_PLIST_LABEL}")

    return plist_file


def uninstall(unload: bool = True) -> None:
    """
    Remove the champi-stt LaunchAgent plist.

    Args:
        unload: Run `launchctl unload` before removing the plist.
    """
    plist_file = _launch_agents_dir() / _PLIST_FILENAME

    if unload and shutil.which("launchctl") and plist_file.exists():
        subprocess.run(
            ["launchctl", "unload", str(plist_file)],
            check=False,
        )
        logger.info(f"LaunchAgent unloaded: {_PLIST_LABEL}")

    if plist_file.exists():
        plist_file.unlink()
        logger.info(f"Removed plist: {plist_file}")
    else:
        logger.warning(f"Plist not found: {plist_file}")


def status() -> str:
    """Return the output of `launchctl list ai.champi.stt`."""
    if not shutil.which("launchctl"):
        return "launchctl not available"
    result = subprocess.run(
        ["launchctl", "list", _PLIST_LABEL],
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr


def is_installed() -> bool:
    """Return True if the plist file is present."""
    return (_launch_agents_dir() / _PLIST_FILENAME).exists()


def is_loaded() -> bool:
    """Return True if the agent is currently loaded in launchctl."""
    if not shutil.which("launchctl"):
        return False
    result = subprocess.run(
        ["launchctl", "list", _PLIST_LABEL],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
