"""MCP tool definitions for champi-stt.

Exposes core STT operations as async functions suitable for registration
as MCP tools.  Every function returns a value on both success and failure —
callers should never see an unhandled exception bubble out of this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import champi_stt


async def list_providers() -> list[str]:
    """Return the names of all available STT providers."""
    return champi_stt.list_providers()


async def get_provider_status(provider: str) -> dict[str, Any]:
    """Return health/status information for a named provider.

    Args:
        provider: Provider key (e.g. ``"whisperlive"``).

    Returns:
        A dict containing model/status info, or an error dict with an
        ``"error"`` key when the provider cannot be reached.
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


async def transcribe_audio(
    audio_path: str,
    language: str | None = None,
    provider: str = "whisperlive",
) -> str:
    """Transcribe a local audio file and return the transcript text.

    Args:
        audio_path: Absolute or relative path to the audio file.
        language: BCP-47 language code hint (``None`` = auto-detect).
        provider: Provider key to use for transcription.

    Returns:
        The transcript string on success, or an error message string when
        the file is missing or transcription fails.
    """
    path = Path(audio_path)
    if not path.exists():
        return f"error: audio file not found: {audio_path}"

    p = champi_stt.get_provider(provider)
    try:
        await p.initialize()
        result = await p.transcribe(str(path), language=language)
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return str(result.get("text", ""))
        return str(result)
    except Exception as exc:
        return f"error: {type(exc).__name__}: {exc}"
    finally:
        await p.shutdown()


async def detect_language(
    audio_path: str,
    provider: str = "whisperlive",
) -> dict[str, Any]:
    """Detect the spoken language in a local audio file.

    Args:
        audio_path: Absolute or relative path to the audio file.
        provider: Provider key to use for language detection.

    Returns:
        A dict with ``"language"`` (BCP-47 code) and ``"probability"``
        (float 0-1) on success, or an error dict with an ``"error"`` key.
    """
    path = Path(audio_path)
    if not path.exists():
        return {
            "error": True,
            "error_type": "FileNotFoundError",
            "error_message": f"audio file not found: {audio_path}",
        }

    p = champi_stt.get_provider(provider)
    try:
        await p.initialize()
        lang_code, probability, _all = await p.detect_language(str(path))
        return {"language": lang_code, "probability": probability}
    except Exception as exc:
        return {
            "error": True,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    finally:
        await p.shutdown()
