"""
Model management for WhisperLive STT service.
Handles model loading, caching, and device optimization without global state.
"""

import asyncio
import dataclasses
import hashlib
import json

# import logging - replaced with loguru
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore[assignment]
    TORCH_AVAILABLE = False
from champi_signals import EventProcessor
from faster_whisper import WhisperModel
from loguru import logger

from champi_stt.providers.whisperlive.config import WhisperLiveConfig
from champi_stt.providers.whisperlive.enums import (
    ComputeType,
    DeviceType,
    LoggingStrings,
)
from champi_stt.providers.whisperlive.events import STTSignalManager
from champi_stt.providers.whisperlive.exceptions import WhisperModelError


@dataclasses.dataclass
class TranscriptionOptions:
    """Options for a transcription request."""

    language: str | None = None
    task: str = "transcribe"
    beam_size: int = 5
    best_of: int = 5
    temperature: float = 0.0
    word_timestamps: bool = False
    vad_filter: bool = False
    vad_threshold: float = 0.5
    initial_prompt: str | None = None


class DeviceManager:
    """Manages device detection and optimization for WhisperLive"""

    @staticmethod
    def auto_detect_device_settings(config: WhisperLiveConfig) -> tuple[str, str]:
        """
        Auto-detect optimal device and compute type settings.

        Returns:
            Tuple of (device, compute_type)
        """
        device = config.device
        compute_type = config.compute_type

        # Default to CPU for stability unless explicitly set to CUDA
        if device is None or device == DeviceType.AUTO.value:
            # Only use CUDA if explicitly enabled via environment variable
            use_cuda = os.getenv("WHISPERLIVE_USE_CUDA", "false").lower() == "true"

            if use_cuda and TORCH_AVAILABLE and torch.cuda.is_available():
                try:
                    # Test if CUDA libraries are working by attempting a simple operation
                    test_tensor = torch.tensor([1.0]).cuda()
                    test_tensor.cpu()  # This will fail if cuDNN libraries are incompatible
                    device = DeviceType.CUDA.value
                    logger.debug("CUDA enabled and libraries working, using GPU")
                except Exception as e:
                    logger.warning(LoggingStrings.CUDA_FALLBACK_TO_CPU.value.format(e))
                    device = DeviceType.CPU.value
            else:
                device = DeviceType.CPU.value

        if compute_type is None or compute_type == ComputeType.AUTO.value:
            if device == DeviceType.CUDA.value:
                try:
                    major, _ = (
                        torch.cuda.get_device_capability()
                        if TORCH_AVAILABLE
                        else (0, 0)
                    )
                    compute_type = (
                        ComputeType.FLOAT16.value
                        if major >= 7
                        else ComputeType.FLOAT32.value
                    )
                except Exception:
                    compute_type = ComputeType.FLOAT32.value
            else:
                compute_type = ComputeType.INT8.value

        return device, compute_type


class ModelCacheManager:
    """Manages model caching without global state"""

    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir)
        self._memory_cache: dict[str, WhisperModel] = {}
        self._cache_lock = asyncio.Lock()

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, config: WhisperLiveConfig) -> str:
        """Generate cache key from model configuration."""
        key_data = f"{config.model_size}:{config.device}:{config.compute_type}:{config.cpu_threads}"
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()[:12]

    def _get_metadata_path(self, cache_key: str) -> Path:
        """Get metadata file path for cache key."""
        return self.cache_dir / f"whisperlive_{cache_key}.json"

    async def save_cache_metadata(
        self, config: WhisperLiveConfig, cache_key: str
    ) -> None:
        """Save cache metadata (since we can't pickle the model)."""
        try:
            metadata_path = self._get_metadata_path(cache_key)
            metadata = {
                "model_size": config.model_size,
                "device": config.device,
                "compute_type": config.compute_type,
                "cpu_threads": config.cpu_threads,
                "cached_at": datetime.now().isoformat(),
                "cache_key": cache_key,
                "note": "Model cached via HuggingFace/faster-whisper cache, not pickle",
            }

            async with asyncio.Lock():  # Ensure atomic write
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

            logger.debug(LoggingStrings.CACHED_MODEL_METADATA.value.format(cache_key))

        except Exception as e:
            logger.error(LoggingStrings.FAILED_TO_CACHE_MODEL.value.format(e))
            raise

    def is_model_cached(self, cache_key: str) -> bool:
        """Check if model metadata exists in cache."""
        metadata_path = self._get_metadata_path(cache_key)
        is_cached = metadata_path.exists()

        return is_cached

    async def get_cached_model(self, cache_key: str) -> WhisperModel | None:
        """Get model from memory cache."""
        async with self._cache_lock:
            if cache_key in self._memory_cache:
                return self._memory_cache[cache_key]
            return None

    async def store_model_in_cache(self, cache_key: str, model: WhisperModel) -> None:
        """Store model in memory cache."""
        async with self._cache_lock:
            self._memory_cache[cache_key] = model

    async def clear_cache(self) -> None:
        """Clear all cached models and metadata."""
        async with self._cache_lock:
            # Clear memory cache
            self._memory_cache.clear()

            # Clear metadata files
            if self.cache_dir.exists():
                for file in self.cache_dir.glob("whisperlive_*.json"):
                    try:
                        file.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to delete cache file {file}: {e}")

        logger.info(f"Cleared WhisperLive cache: {self.cache_dir}")

    def get_cache_info(self) -> dict[str, Any]:
        """Get cache statistics."""
        if not self.cache_dir.exists():
            return {"files": 0, "size_kb": 0, "memory_cached": 0}

        files = list(self.cache_dir.glob("whisperlive_*.json"))
        total_size = sum(f.stat().st_size for f in files) if files else 0

        return {
            "files": len(files),
            "size_kb": total_size / 1024,
            "memory_cached": len(self._memory_cache),
            "files_list": [f.name for f in files],
            "memory_keys": list(self._memory_cache.keys()),
            "note": "WhisperLive models use HuggingFace cache (not pickled)",
        }


class ModelManager:
    """Manages WhisperLive model loading and lifecycle"""

    def __init__(self, config: WhisperLiveConfig):
        self.config = config
        self.cache_manager = ModelCacheManager(config.cache_dir)
        self._model: WhisperModel | None = None
        self._model_key: str | None = None
        self.signal_manager = STTSignalManager()

    class Meta:
        event_type = "model"
        signal_manager = STTSignalManager()

    @EventProcessor.emits_event(data=["device", "compute_type", "cache_key"])
    async def initialize(self) -> WhisperModel:
        """Initialize and load the model with comprehensive event emissions."""
        if self._model is not None:
            return self._model

        try:
            # Auto-detect device settings
            device, compute_type = DeviceManager.auto_detect_device_settings(
                self.config
            )
            self.config.device = device
            self.config.compute_type = compute_type

            logger.debug(
                LoggingStrings.DEVICE_AUTO_DETECTED.value.format(device, compute_type)
            )

            # Emit device detection event
            self.Meta.signal_manager.model.send(
                self,
                event_type="model",
                sub_event="device_detected",
                data={"device": device, "compute_type": compute_type},
            )

            # Generate cache key
            self._model_key = self.cache_manager._get_cache_key(self.config)

            # Try memory cache first
            cached_model = await self.cache_manager.get_cached_model(self._model_key)
            if cached_model is not None:
                logger.info(LoggingStrings.LOADING_FROM_MEMORY_CACHE.value)

                # Emit memory cache hit event
                self.Meta.signal_manager.model.send(
                    self,
                    event_type="model",
                    sub_event="cache_hit",
                    data={"cache_type": "memory", "cache_key": self._model_key},
                )

                self._model = cached_model
                return self._model

            # Check if model was previously loaded (metadata exists)
            if self.cache_manager.is_model_cached(self._model_key):
                logger.info(LoggingStrings.LOADING_FROM_DISK_CACHE.value)

                # Emit disk cache hit event
                self.Meta.signal_manager.model.send(
                    self,
                    event_type="model",
                    sub_event="cache_hit",
                    data={"cache_type": "disk", "cache_key": self._model_key},
                )
            else:
                logger.info(LoggingStrings.LOADING_FROM_SCRATCH.value)

                # Emit cache miss event
                self.Meta.signal_manager.model.send(
                    self,
                    event_type="model",
                    sub_event="cache_miss",
                    data={"cache_key": self._model_key},
                )

            # Load the model
            self._model = await self._load_model()

            # Emit model loaded event
            self.Meta.signal_manager.model.send(
                self,
                event_type="model",
                sub_event="model_loaded",
                data={
                    "model_size": self.config.model_size,
                    "device": self.config.device,
                    "compute_type": self.config.compute_type,
                    "cache_key": self._model_key,
                },
            )

            # Store in memory cache
            await self.cache_manager.store_model_in_cache(self._model_key, self._model)

            # Save metadata
            if not self.cache_manager.is_model_cached(self._model_key):
                await self.cache_manager.save_cache_metadata(
                    self.config, self._model_key
                )

            logger.debug(LoggingStrings.PROVIDER_INITIALIZED.value)

            return self._model

        except Exception as e:
            logger.error(f"Model initialization failed: {e}")

            # Emit error event
            self.Meta.signal_manager.model.send(
                self,
                event_type="model",
                sub_event="initialization_error",
                data={"error": str(e)},
            )

            raise WhisperModelError(f"Model initialization failed: {e}") from e

    async def _load_model(self) -> WhisperModel:
        """Load WhisperModel with fallback handling."""
        start_time = time.time()

        try:
            model = WhisperModel(
                model_size_or_path=self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
                cpu_threads=self.config.cpu_threads,
                download_root=str(self.config.cache_dir),
            )
        except Exception as e:
            # If CUDA fails (e.g., cuDNN issues), fall back to CPU
            if "cuda" in str(e).lower() or "cudnn" in str(e).lower():
                logger.warning(LoggingStrings.CUDA_FALLBACK_TO_CPU.value.format(e))

                self.config.device = DeviceType.CPU.value
                self.config.compute_type = ComputeType.INT8.value

                # Update cache key for CPU model
                self._model_key = self.cache_manager._get_cache_key(self.config)

                model = WhisperModel(
                    model_size_or_path=self.config.model_size,
                    device=self.config.device,
                    compute_type=self.config.compute_type,
                    cpu_threads=self.config.cpu_threads,
                    download_root=str(self.config.cache_dir),
                )
            else:
                raise

        load_time = time.time() - start_time
        logger.debug(LoggingStrings.MODEL_LOADED_TIME.value.format(load_time))

        return model

    @property
    def model(self) -> WhisperModel | None:
        """Get the loaded model instance."""
        return self._model

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None

    async def get_model_info(self) -> dict[str, Any]:
        """Get information about the loaded model."""
        if not self.is_loaded:
            return {"status": "not_loaded"}

        info = {
            "status": "loaded",
            "model_size": self.config.model_size,
            "device": self.config.device,
            "compute_type": self.config.compute_type,
            "cache_key": self._model_key,
            "is_multilingual": self._model.model.is_multilingual,
            "supported_languages": list(self._model.supported_languages)
            if hasattr(self._model, "supported_languages")
            else [],
            "cache": self.cache_manager.get_cache_info(),
        }

        # Add cache info

        return info

    async def unload(self) -> None:
        """Unload the model and clear resources."""
        if self._model is not None:
            self._model = None
            self._model_key = None
            logger.debug(LoggingStrings.PROVIDER_UNLOADED.value)

    async def clear_cache(self) -> None:
        """Clear model cache."""
        await self.cache_manager.clear_cache()
        await self.unload()
