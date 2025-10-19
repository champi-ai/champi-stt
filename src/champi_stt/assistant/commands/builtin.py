"""
Built-in voice commands
"""

import asyncio
# import logging - replaced with loguru
from datetime import datetime

from loguru import logger


# Time and date commands

async def say_time():
    """Say current time"""
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    logger.info(f"Current time: {time_str}")
    return f"The time is {time_str}"


async def say_date():
    """Say current date"""
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    logger.info(f"Current date: {date_str}")
    return f"Today is {date_str}"


# System commands

async def shutdown_assistant():
    """Shutdown the voice assistant"""
    logger.info("Shutting down assistant...")
    return {"action": "shutdown", "message": "Goodbye!"}


async def restart_assistant():
    """Restart the voice assistant"""
    logger.info("Restarting assistant...")
    return {"action": "restart", "message": "Restarting..."}


# Information commands

async def get_system_info():
    """Get system information"""
    import platform
    import psutil

    info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
    }

    logger.info(f"System info: {info}")
    return info


# Web commands

async def web_search(query: str):
    """
    Perform web search.

    Args:
        query: Search query
    """
    import webbrowser
    search_url = f"https://www.google.com/search?q={query}"
    webbrowser.open(search_url)
    logger.info(f"Opening web search for: {query}")
    return f"Searching for {query}"


async def open_url(url: str):
    """
    Open URL in browser.

    Args:
        url: URL to open
    """
    import webbrowser
    webbrowser.open(url)
    logger.info(f"Opening URL: {url}")
    return f"Opening {url}"


# Application commands

async def open_application(app_name: str):
    """
    Open application by name.

    Args:
        app_name: Application name
    """
    import subprocess
    import platform

    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", app_name])
        elif system == "Linux":
            subprocess.Popen([app_name.lower()])
        elif system == "Windows":
            subprocess.Popen(["start", app_name], shell=True)

        logger.info(f"Opening application: {app_name}")
        return f"Opening {app_name}"

    except Exception as e:
        logger.error(f"Failed to open application: {e}")
        return f"Could not open {app_name}"


# Voice feedback

async def say_hello():
    """Say hello"""
    return "Hello! How can I help you?"


async def say_goodbye():
    """Say goodbye"""
    return "Goodbye!"


async def say_thanks():
    """Acknowledge thanks"""
    return "You're welcome!"


# Media control

async def set_volume(level: str):
    """
    Set system volume.

    Args:
        level: Volume level (0-100)
    """
    import platform
    import subprocess

    system = platform.system()

    try:
        volume = int(level)
        if not (0 <= volume <= 100):
            return "Volume must be between 0 and 100"

        if system == "Linux":
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume}%"])
        elif system == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {volume}"])
        elif system == "Windows":
            # Windows volume control via PowerShell
            ps_cmd = f"[audio]::Volume = {volume / 100.0}"
            subprocess.run(["powershell", "-Command", ps_cmd])

        logger.info(f"Volume set to {volume}%")
        return f"Volume set to {volume} percent"

    except Exception as e:
        logger.error(f"Failed to set volume: {e}")
        return "Could not set volume"


async def play_pause_media():
    """Play/pause media"""
    import platform
    import subprocess

    system = platform.system()

    try:
        if system == "Linux":
            subprocess.run(["playerctl", "play-pause"])
        elif system == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Spotify" to playpause'])
        # Windows support can be added

        logger.info("Toggled play/pause")
        return "Toggled play/pause"

    except Exception as e:
        logger.error(f"Failed to control media: {e}")
        return "Could not control media"


# Helper to register all built-in commands

def register_builtin_commands(registry):
    """
    Register all built-in commands.

    Args:
        registry: CommandRegistry instance
    """
    # Time commands
    registry.register_exact("what time is it", say_time, "Get current time")
    registry.register_exact("what's the time", say_time, "Get current time")
    registry.register_exact("what date is it", say_date, "Get current date")
    registry.register_exact("what's the date", say_date, "Get current date")

    # System commands
    registry.register_exact("shutdown", shutdown_assistant, "Shutdown assistant")
    registry.register_exact("restart", restart_assistant, "Restart assistant")
    registry.register_exact("system info", get_system_info, "Get system information")

    # Greetings
    registry.register_exact("hello", say_hello, "Say hello")
    registry.register_exact("hi", say_hello, "Say hello")
    registry.register_exact("goodbye", say_goodbye, "Say goodbye")
    registry.register_exact("bye", say_goodbye, "Say goodbye")
    registry.register_exact("thank you", say_thanks, "Acknowledge thanks")
    registry.register_exact("thanks", say_thanks, "Acknowledge thanks")

    # Pattern commands
    registry.register_pattern(
        r"search for (?P<query>.+)",
        web_search,
        "Search the web"
    )
    registry.register_pattern(
        r"open (?P<url>https?://.+)",
        open_url,
        "Open URL in browser"
    )
    registry.register_pattern(
        r"open (?P<app_name>\w+)",
        open_application,
        "Open application"
    )
    registry.register_pattern(
        r"set volume to (?P<level>\d+)",
        set_volume,
        "Set system volume"
    )
    registry.register_pattern(
        r"volume (?P<level>\d+)",
        set_volume,
        "Set system volume"
    )

    logger.info("✓ Built-in commands registered")
