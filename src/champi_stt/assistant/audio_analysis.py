"""Audio analysis utilities for real-time audio visualization.

Provides functions to analyze audio chunks for:
- RMS level (decibels)
- Dominant frequency (Hz)
- Voice activity detection
"""

import numpy as np
from typing import Tuple


def calculate_rms_db(audio_data: np.ndarray, reference: float = 32768.0) -> float:
    """Calculate RMS level in decibels.

    Args:
        audio_data: Audio samples (int16 or float32)
        reference: Reference level for dB calculation (32768 for int16)

    Returns:
        RMS level in dB (typically -60 to 0)
    """
    if len(audio_data) == 0:
        return -60.0

    # Convert to float if needed
    if audio_data.dtype == np.int16:
        audio_float = audio_data.astype(np.float32) / reference
    else:
        audio_float = audio_data.astype(np.float32)

    # Calculate RMS
    rms = np.sqrt(np.mean(audio_float**2))

    # Convert to dB, with floor at -60dB
    if rms > 0:
        db = 20 * np.log10(rms)
        return max(-60.0, db)
    else:
        return -60.0


def calculate_dominant_frequency(
    audio_data: np.ndarray, sample_rate: int = 16000, min_freq: float = 80.0
) -> float:
    """Calculate dominant frequency using FFT.

    Args:
        audio_data: Audio samples (int16 or float32)
        sample_rate: Sample rate in Hz
        min_freq: Minimum frequency to consider (Hz)

    Returns:
        Dominant frequency in Hz (0 if no significant frequency)
    """
    if len(audio_data) < 256:
        return 0.0

    # Convert to float if needed
    if audio_data.dtype == np.int16:
        audio_float = audio_data.astype(np.float32) / 32768.0
    else:
        audio_float = audio_data.astype(np.float32)

    # Apply window to reduce spectral leakage
    window = np.hanning(len(audio_float))
    audio_windowed = audio_float * window

    # Compute FFT
    fft = np.fft.rfft(audio_windowed)
    magnitudes = np.abs(fft)

    # Get frequencies for each bin
    freqs = np.fft.rfftfreq(len(audio_windowed), 1.0 / sample_rate)

    # Filter out frequencies below minimum
    valid_indices = freqs >= min_freq
    if not np.any(valid_indices):
        return 0.0

    filtered_mags = magnitudes[valid_indices]
    filtered_freqs = freqs[valid_indices]

    # Find peak frequency
    if len(filtered_mags) == 0:
        return 0.0

    peak_idx = np.argmax(filtered_mags)
    dominant_freq = filtered_freqs[peak_idx]

    # Only return if magnitude is significant
    if filtered_mags[peak_idx] < 0.01 * np.max(magnitudes):
        return 0.0

    return float(dominant_freq)


def detect_voice_activity(
    audio_data: np.ndarray, threshold_db: float = -40.0, sample_rate: int = 16000
) -> bool:
    """Simple voice activity detection based on RMS level and frequency content.

    Args:
        audio_data: Audio samples (int16 or float32)
        threshold_db: dB threshold for voice activity
        sample_rate: Sample rate in Hz

    Returns:
        True if voice activity is detected, False otherwise
    """
    # Check RMS level
    rms_db = calculate_rms_db(audio_data)
    if rms_db < threshold_db:
        return False

    # Check if there's significant energy in voice frequency range (80-3000 Hz)
    dominant_freq = calculate_dominant_frequency(audio_data, sample_rate)

    # Voice is typically between 80-3000 Hz
    if 80 <= dominant_freq <= 3000:
        return True

    return False


def analyze_audio_chunk(
    audio_data: np.ndarray, sample_rate: int = 16000
) -> Tuple[float, float, bool]:
    """Analyze audio chunk for all metrics.

    Args:
        audio_data: Audio samples (int16 or float32)
        sample_rate: Sample rate in Hz

    Returns:
        Tuple of (rms_db, dominant_freq, is_speaking)
    """
    rms_db = calculate_rms_db(audio_data)
    dominant_freq = calculate_dominant_frequency(audio_data, sample_rate)
    is_speaking = detect_voice_activity(audio_data, sample_rate=sample_rate)

    return rms_db, dominant_freq, is_speaking


# Test/demo code
if __name__ == "__main__":
    # Generate test audio
    duration = 1.0
    sample_rate = 16000
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Test with 440 Hz tone (A4 note)
    tone = np.sin(2 * np.pi * 440 * t) * 0.5
    tone_int16 = (tone * 32767).astype(np.int16)

    print("Analyzing 440 Hz tone:")
    rms_db, freq, speaking = analyze_audio_chunk(tone_int16, sample_rate)
    print(f"  RMS: {rms_db:.1f} dB")
    print(f"  Dominant frequency: {freq:.0f} Hz")
    print(f"  Voice detected: {speaking}")

    # Test with silence
    silence = np.zeros(int(sample_rate * 0.5), dtype=np.int16)
    print("\nAnalyzing silence:")
    rms_db, freq, speaking = analyze_audio_chunk(silence, sample_rate)
    print(f"  RMS: {rms_db:.1f} dB")
    print(f"  Dominant frequency: {freq:.0f} Hz")
    print(f"  Voice detected: {speaking}")
