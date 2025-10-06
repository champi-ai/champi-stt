"""
Provider factory for creating STT providers
"""

from typing import Literal

from champi_stt.core.base_provider import BaseSTTProvider
from champi_stt.core.base_config import BaseSTTConfig

# Type for supported providers
ProviderType = Literal["whisperlive"]  # Will add "openai", "deepgram", etc.


def get_provider(
    provider_type: ProviderType = "whisperlive",
    config: BaseSTTConfig | None = None,
    **config_kwargs
) -> BaseSTTProvider:
    """
    Factory function to create STT providers.

    Args:
        provider_type: Type of provider ("whisperlive", "openai", etc.)
        config: Pre-configured provider config (optional)
        **config_kwargs: Config parameters (if config not provided)

    Returns:
        Initialized STT provider instance

    Examples:
        # Using default config from environment
        provider = get_provider("whisperlive")

        # Using custom config
        from champi_stt.providers.whisperlive import WhisperLiveConfig
        config = WhisperLiveConfig(model_size="base", device="cpu")
        provider = get_provider("whisperlive", config=config)

        # Using kwargs
        provider = get_provider("whisperlive", model_size="base", device="cpu")
    """
    if provider_type == "whisperlive":
        from champi_stt.providers.whisperlive import (
            WhisperLiveConfig,
            WhisperLiveSTTProvider,
        )

        if config is None:
            if config_kwargs:
                # Create config from kwargs
                config = WhisperLiveConfig(**config_kwargs)
            else:
                # Load from environment
                config = WhisperLiveConfig.from_env()

        return WhisperLiveSTTProvider(config=config)

    # Future providers:
    # elif provider_type == "openai":
    #     from champi_stt.providers.openai import OpenAIConfig, OpenAISTTProvider
    #     config = config or OpenAIConfig.from_env()
    #     return OpenAISTTProvider(config=config)
    #
    # elif provider_type == "deepgram":
    #     from champi_stt.providers.deepgram import DeepgramConfig, DeepgramSTTProvider
    #     config = config or DeepgramConfig.from_env()
    #     return DeepgramSTTProvider(config=config)

    else:
        raise ValueError(
            f"Unknown provider type: {provider_type}. "
            f"Supported providers: whisperlive"
        )


def list_providers() -> list[str]:
    """
    Get list of available STT providers.

    Returns:
        List of provider names
    """
    return ["whisperlive"]  # Will grow as we add more providers


def get_default_provider() -> BaseSTTProvider:
    """
    Get the default STT provider (WhisperLive).

    Returns:
        Default provider instance
    """
    return get_provider("whisperlive")
