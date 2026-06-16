"""Configuration for the Kokoro STT provider."""

import os
from dataclasses import dataclass

from champi_stt.core.base_config import BaseSTTConfig


@dataclass
class KokoroConfig(BaseSTTConfig):
    """Configuration for the Kokoro local STT provider."""

    # Model repository ID used by kokoro at initialisation time
    model_id: str = "hexgrad/Kokoro-82M"

    # BCP-47 language code passed to the kokoro pipeline.
    # kokoro uses single-letter codes internally; 'a' = American English.
    lang_code: str = "a"

    # Inference device: "cpu" or "cuda"
    device: str = "cpu"

    @classmethod
    def from_env(cls) -> "KokoroConfig":
        """Create a KokoroConfig from environment variables.

        Reads:
          KOKORO_MODEL_ID  — model repository ID (default: hexgrad/Kokoro-82M)
          KOKORO_LANG_CODE — language code (default: a)
          KOKORO_DEVICE    — inference device (default: cpu)
        """
        return cls(
            model_id=os.environ.get("KOKORO_MODEL_ID", "hexgrad/Kokoro-82M"),
            lang_code=os.environ.get("KOKORO_LANG_CODE", "a"),
            device=os.environ.get("KOKORO_DEVICE", "cpu"),
        )
