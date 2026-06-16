"""Provider factory for creating STT providers.

This is the primary entry point for instantiating STT providers.
Use :func:`get_provider` to create any supported provider by key.
"""

from typing import Any

from champi_stt.core.base_provider import BaseSTTProvider

_SUPPORTED_PROVIDERS = [
    "whisperlive",
    "openai_whisper",
    "deepgram",
    "assemblyai",
    "kokoro",
]


def get_provider(
    provider_type: str = "whisperlive",
    config: Any | None = None,
    **config_kwargs,
) -> BaseSTTProvider:
    """
    Factory function to create STT providers.

    Args:
        provider_type: Provider key — "whisperlive", "openai_whisper", "deepgram", "assemblyai", or "kokoro"
        config: Pre-built provider config object (optional)
        **config_kwargs: Config fields forwarded to the config constructor

    Returns:
        Provider instance (not yet initialized — call initialize() before use)
    """
    if provider_type == "whisperlive":
        from champi_stt.providers.whisperlive import (
            WhisperLiveConfig,
            WhisperLiveSTTProvider,
        )

        if config is None:
            config = (
                WhisperLiveConfig(**config_kwargs)
                if config_kwargs
                else WhisperLiveConfig.from_env()
            )
        return WhisperLiveSTTProvider(config=config)

    if provider_type == "openai_whisper":
        from champi_stt.providers.openai_whisper import (
            OpenAIWhisperConfig,
            OpenAIWhisperProvider,
        )

        if config is None:
            config = (
                OpenAIWhisperConfig(**config_kwargs)
                if config_kwargs
                else OpenAIWhisperConfig.from_env()
            )
        return OpenAIWhisperProvider(config=config)

    if provider_type == "deepgram":
        from champi_stt.providers.deepgram import DeepgramConfig, DeepgramProvider

        if config is None:
            config = (
                DeepgramConfig(**config_kwargs)
                if config_kwargs
                else DeepgramConfig.from_env()
            )
        return DeepgramProvider(config=config)

    if provider_type == "assemblyai":
        from champi_stt.providers.assemblyai import AssemblyAIConfig, AssemblyAIProvider

        if config is None:
            config = (
                AssemblyAIConfig(**config_kwargs)
                if config_kwargs
                else AssemblyAIConfig.from_env()
            )
        return AssemblyAIProvider(config=config)

    if provider_type == "kokoro":
        from champi_stt.providers.kokoro import KokoroConfig, KokoroSTTProvider

        if config is None:
            config = (
                KokoroConfig(**config_kwargs)
                if config_kwargs
                else KokoroConfig.from_env()
            )
        return KokoroSTTProvider(config=config)

    raise ValueError(
        f"Unknown provider type: {provider_type!r}. "
        f"Supported providers: {', '.join(_SUPPORTED_PROVIDERS)}"
    )


def list_providers() -> list[str]:
    """Return the list of registered provider keys.

    Returns:
        List of provider key strings accepted by :func:`get_provider`.
    """
    return list(_SUPPORTED_PROVIDERS)


def get_default_provider() -> BaseSTTProvider:
    """Return the default provider (WhisperLive, local inference).

    Returns:
        An uninitialized :class:`~champi_stt.core.base_provider.BaseSTTProvider`
        backed by WhisperLive.
    """
    return get_provider("whisperlive")
