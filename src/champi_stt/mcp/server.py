"""
MCP server for champi-stt.

Exposes champi-stt transcription capabilities over the Model Context Protocol
so that MCP-aware hosts (Claude Desktop, Cursor, etc.) can call STT tools.

Supported transports
--------------------
* ``stdio`` (default) — JSON-RPC over stdin/stdout; stdout MUST stay clean.
* ``sse`` — Server-Sent Events over HTTP for remote/mobile clients.

Provider lifecycle
------------------
The provider is initialised lazily on the first tool call and shut down
cleanly via the FastMCP lifespan context manager — the same pattern used
by champi-imgui. No atexit hacks, no asyncio.run() in a signal handler.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import sys
from contextlib import asynccontextmanager
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

from loguru import logger as _logger

try:
    from mcp.server.fastmcp import FastMCP as _FastMCP

    MCP_AVAILABLE = True
except ImportError:
    _FastMCP = None  # type: ignore[assignment,misc]
    MCP_AVAILABLE = False

_DEFAULT_PROVIDER = "whisperlive"


def _require_mcp() -> None:
    if not MCP_AVAILABLE:
        _v = _pkg_version("champi-stt")
        _whl = f"champi_stt-{_v}-py3-none-any.whl"
        _url = f"https://github.com/champi-ai/champi-stt/releases/download/v{_v}/{_whl}"
        raise ImportError(
            "mcp is required for the MCP server. "
            f'Install with: uvx --from "champi-stt[mcp] @ {_url}" champi-stt mcp serve'
        )


def create_mcp_server() -> Any:
    """Build and return a configured FastMCP server instance.

    All tool functions are registered here as closures over a shared
    mutable state dict, matching the champi-imgui factory pattern.
    The lifespan context manager handles provider shutdown on exit.

    Returns:
        Configured FastMCP application ready for ``mcp.run()``.
    """
    import champi_stt

    # Shared mutable state — avoids module-level globals
    state: dict[str, Any] = {"provider": None, "lock": None}

    async def _get_provider(provider_name: str) -> Any:
        if state["lock"] is None:
            state["lock"] = asyncio.Lock()
        async with state["lock"]:
            if state["provider"] is None:
                _logger.info(
                    "[champi-stt] Initializing provider '{}'... (first call may be slow)",
                    provider_name,
                )
                p = champi_stt.get_provider(provider_name)
                await p.initialize()
                state["provider"] = p
        return state["provider"]

    @asynccontextmanager
    async def _lifespan(app: Any) -> Any:
        try:
            yield
        finally:
            if state["provider"] is not None:
                with contextlib.suppress(Exception):
                    await state["provider"].shutdown()
                state["provider"] = None

    mcp = _FastMCP("champi-stt", lifespan=_lifespan)

    # Expose state for test injection (mirrors champi-imgui pattern)
    mcp._state = state  # type: ignore[attr-defined]

    @mcp.tool()
    def list_providers() -> list[str]:
        """Return the names of all available STT providers."""
        return champi_stt.list_providers()

    @mcp.tool()
    async def get_provider_status(provider: str) -> dict[str, Any]:
        """Return health/status information for a named provider.

        Args:
            provider: Provider key (e.g. ``"whisperlive"``).
        """
        try:
            p = champi_stt.get_provider(provider)
            return await p.get_model_info()
        except Exception as exc:
            return {
                "error": True,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "provider": provider,
            }

    @mcp.tool()
    async def transcribe_audio(
        audio_path: str,
        language: str | None = None,
        provider: str | None = None,
    ) -> str:
        """Transcribe a local audio file and return the transcript text.

        Args:
            audio_path: Absolute or relative path to the audio file.
            language: BCP-47 language code hint (``None`` = auto-detect).
            provider: Provider key. Falls back to ``CHAMPI_STT_PROVIDER``
                env var, then ``"whisperlive"``.
        """
        path = Path(audio_path)
        if not path.exists():
            return f"error: audio file not found: {audio_path}"

        effective = (
            provider or os.environ.get("CHAMPI_STT_PROVIDER") or _DEFAULT_PROVIDER
        )
        try:
            p = await _get_provider(effective)
            result = await p.transcribe(str(path), language=language)
            if isinstance(result, str):
                return result
            if isinstance(result, dict):
                return str(result.get("text", ""))
            return str(result)
        except Exception as exc:
            return f"error: {type(exc).__name__}: {exc}"

    @mcp.tool()
    async def detect_language(
        audio_path: str,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Detect the spoken language in a local audio file.

        Args:
            audio_path: Absolute or relative path to the audio file.
            provider: Provider key. Falls back to ``CHAMPI_STT_PROVIDER``
                env var, then ``"whisperlive"``.
        """
        path = Path(audio_path)
        if not path.exists():
            return {
                "error": True,
                "error_type": "FileNotFoundError",
                "error_message": f"audio file not found: {audio_path}",
            }

        effective = (
            provider or os.environ.get("CHAMPI_STT_PROVIDER") or _DEFAULT_PROVIDER
        )
        try:
            p = await _get_provider(effective)
            lang_code, probability, _all = await p.detect_language(str(path))
            return {"language": lang_code, "probability": probability}
        except Exception as exc:
            return {
                "error": True,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }

    from champi_stt.mcp.mic_tools import listen_once as _listen_once

    @mcp.tool()
    async def listen_once_tool(
        duration_seconds: float = 5.0,
        language: str | None = None,
        provider: str | None = None,
        device_index: int | None = None,
    ) -> str:
        """Record audio from a microphone for a fixed duration and return the transcription.

        Args:
            duration_seconds: Recording length in seconds.
            language: BCP-47 language code hint (``None`` = auto-detect).
            provider: Provider key. Falls back to ``CHAMPI_STT_PROVIDER`` env var,
                then ``"whisperlive"``.
            device_index: Input device index. Falls back to
                ``CHAMPI_INPUT_DEVICE_INDEX`` env var, then the system default.
        """
        return await _listen_once(duration_seconds, language, provider, device_index)

    from champi_stt.mcp.mic_tools import listen_until_silence as _listen_until_silence

    @mcp.tool()
    async def listen_until_silence_tool(
        max_duration_seconds: float = 30.0,
        silence_threshold_ms: int = 800,
        language: str | None = None,
        provider: str | None = None,
        device_index: int | None = None,
    ) -> str:
        """Record from a microphone until silence is detected (VAD), then return the transcription.

        Args:
            max_duration_seconds: Hard upper limit on recording length in seconds.
            silence_threshold_ms: Consecutive silence in milliseconds that triggers stop.
            language: BCP-47 language code hint (``None`` = auto-detect).
            provider: Provider key. Falls back to ``CHAMPI_STT_PROVIDER`` env var,
                then ``"whisperlive"``.
            device_index: Input device index. Falls back to
                ``CHAMPI_INPUT_DEVICE_INDEX`` env var, then the system default.
        """
        return await _listen_until_silence(
            max_duration_seconds, silence_threshold_ms, language, provider, device_index
        )

    from champi_stt.mcp.mic_tools import list_audio_devices as _list_audio_devices

    @mcp.tool()
    def list_audio_devices_tool() -> list[dict[str, object]]:
        """List available audio input devices."""
        try:
            return _list_audio_devices()
        except ImportError as exc:
            return [{"error": str(exc)}]

    return mcp


# Module-level instance created on import (when mcp package is available)
mcp: Any = create_mcp_server() if MCP_AVAILABLE else None


def main(
    transport: str = "stdio",
    host: str = "localhost",
    port: int = 8765,
) -> None:
    """Start the MCP server.

    Args:
        transport: ``"stdio"`` or ``"sse"``.
        host: Bind address (SSE only).
        port: Port (SSE only).
    """
    _require_mcp()

    from loguru import logger

    logger.remove()
    logger.add(sys.stderr)

    assert mcp is not None

    if transport == "sse":
        mcp.settings.host = host
        mcp.settings.port = port

    mcp.run(transport=transport)  # type: ignore[arg-type]
