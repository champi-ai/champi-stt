"""
Generic response formatting utilities for all STT providers.

Provides standardized response formatting across different providers.
"""

from typing import Any
from loguru import logger


def format_response(
    result: dict[str, Any],
    response_format: str
) -> str | dict[str, Any]:
    """
    Format transcription response based on requested format.

    Args:
        result: Raw transcription result dict with at minimum "text" key
        response_format: Output format ("json", "text", "verbose_json")

    Returns:
        Formatted response (type depends on format)
    """
    if response_format == "json":
        # Simple JSON with just text
        formatted = {"text": result.get("text", "")}
        logger.debug(f"Formatted as JSON: {formatted}")
        return formatted

    elif response_format == "text":
        # Plain text only
        text = result.get("text", "")
        logger.debug(f"Formatted as text: '{text}'")
        return text

    elif response_format == "verbose_json":
        # Full verbose JSON with all metadata
        verbose = format_verbose_json(result)
        logger.debug(f"Formatted as verbose JSON: {verbose}")
        return verbose

    else:
        # Unknown format, return raw result
        logger.warning(f"Unknown response_format '{response_format}', returning raw result")
        return result


def format_verbose_json(result: dict[str, Any]) -> dict[str, Any]:
    """
    Format as verbose JSON with all available metadata.

    Args:
        result: Raw transcription result

    Returns:
        Verbose JSON response
    """
    verbose = {
        "text": result.get("text", ""),
        "language": result.get("language", "unknown"),
        "duration": result.get("duration", 0.0),
    }

    # Add optional fields if present
    if "task" in result:
        verbose["task"] = result["task"]

    if "language_probability" in result:
        verbose["language_probability"] = result["language_probability"]

    if "duration_after_vad" in result:
        verbose["duration_after_vad"] = result["duration_after_vad"]

    if "processing_time" in result:
        verbose["processing_time"] = result["processing_time"]

    # Add segments if available
    if "segments" in result:
        verbose["segments"] = [
            format_segment(seg) for seg in result["segments"]
        ]

    return verbose


def format_segment(segment: dict[str, Any]) -> dict[str, Any]:
    """
    Format a single transcription segment.

    Args:
        segment: Raw segment data

    Returns:
        Formatted segment
    """
    formatted = {
        "id": segment.get("id", 0),
        "start": segment.get("start", 0.0),
        "end": segment.get("end", 0.0),
        "text": segment.get("text", ""),
    }

    # Add optional segment fields
    optional_fields = [
        "tokens",
        "temperature",
        "avg_logprob",
        "compression_ratio",
        "no_speech_prob",
        "seek",
        "words",
    ]

    for field in optional_fields:
        if field in segment:
            formatted[field] = segment[field]

    return formatted


def standardize_provider_response(
    provider_result: Any,
    provider_name: str
) -> dict[str, Any]:
    """
    Standardize different provider responses to a common format.

    Args:
        provider_result: Raw result from provider
        provider_name: Name of the provider ("whisperlive", "openai", etc.)

    Returns:
        Standardized response dict with at minimum:
        - text: transcription text
        - language: detected language (if available)
        - duration: audio duration (if available)
    """
    if provider_name == "whisperlive":
        # WhisperLive already returns dict format
        return provider_result

    elif provider_name == "openai":
        # OpenAI Whisper API returns different format
        # This is a placeholder for future implementation
        if isinstance(provider_result, dict):
            return {
                "text": provider_result.get("text", ""),
                "language": provider_result.get("language", "unknown"),
                "duration": provider_result.get("duration", 0.0),
            }

    # Default: return as-is if dict, wrap if string
    if isinstance(provider_result, str):
        return {"text": provider_result}
    elif isinstance(provider_result, dict):
        return provider_result
    else:
        return {"text": str(provider_result)}


def create_error_response(error: Exception) -> dict[str, Any]:
    """
    Create standardized error response.

    Args:
        error: The exception that occurred

    Returns:
        Error response dict
    """
    return {
        "error": True,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "text": "",
    }
