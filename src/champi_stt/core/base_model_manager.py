"""
Base model manager interface
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseModelManager(ABC):
    """
    Abstract base class for model management.

    Model managers handle loading, caching, and lifecycle of ML models.
    Cloud providers may not need this (can implement as pass-through).
    """

    @abstractmethod
    async def initialize(self) -> Any:
        """
        Initialize and load the model.

        Returns:
            The loaded model instance (type varies by provider)
        """
        pass

    @abstractmethod
    async def unload(self) -> None:
        """Unload the model and free resources"""
        pass

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if model is currently loaded"""
        pass

    @abstractmethod
    async def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model metadata (format varies by provider)
        """
        pass

    # Optional methods

    async def clear_cache(self) -> None:  # noqa: B027
        """
        Clear model cache.

        Default implementation does nothing.
        Providers with caching should override.
        """
        pass

    @property
    def model(self) -> Any | None:
        """
        Get the loaded model instance.

        Default implementation returns None.
        Providers should override to return their model.
        """
        return None
