"""AssemblyAI provider configuration."""

import os
from dataclasses import dataclass

from champi_stt.core.base_config import BaseSTTConfig


@dataclass
class AssemblyAIConfig(BaseSTTConfig):
    """Configuration for the AssemblyAI STT provider."""

    api_key: str = ""
    sample_rate: int = 16000
    encoding: str = "pcm_s16le"
    word_boost: list[str] | None = None
    disable_partial_transcripts: bool = False
    end_utterance_silence_threshold: int = 700

    @classmethod
    def from_env(cls) -> "AssemblyAIConfig":
        return cls(
            api_key=os.environ.get("ASSEMBLYAI_API_KEY", ""),
            sample_rate=int(os.environ.get("ASSEMBLYAI_SAMPLE_RATE", "16000")),
        )
