"""
champi-stt CLI entry point
"""

import asyncio
import sys
from pathlib import Path

from champi_stt import WhisperLiveConfig, WhisperLiveSTTProvider


async def transcribe_file(audio_file: str):
    """Transcribe an audio file using champi-stt"""
    config = WhisperLiveConfig.from_env()
    provider = WhisperLiveSTTProvider(config=config)

    await provider.initialize()

    result = await provider.transcribe(audio_file)

    if isinstance(result, dict):
        print(f"\nTranscription: {result.get('text', '')}")
        print(f"Language: {result.get('language', 'N/A')}")
        print(f"Duration: {result.get('duration', 0):.2f}s")
    else:
        print(f"\nTranscription: {result}")

    await provider.shutdown()


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: champi-stt <audio_file>")
        print("\nExample: champi-stt audio.wav")
        sys.exit(1)

    audio_file = sys.argv[1]

    if not Path(audio_file).exists():
        print(f"Error: File not found: {audio_file}")
        sys.exit(1)

    try:
        asyncio.run(transcribe_file(audio_file))
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
