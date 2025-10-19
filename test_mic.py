#!/usr/bin/env python3
"""Quick microphone test"""
import sounddevice as sd
import numpy as np
import time

print("Testing microphone input...")
print("\nAvailable input devices:")
devices = sd.query_devices()
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        print(f"  [{i}] {device['name']} - {device['default_samplerate']} Hz")

# Use device 0 (USB Condenser Microphone)
device_id = 0
sample_rate = 44100
duration = 3

print(f"\nRecording {duration} seconds from device {device_id}...")
print("SPEAK NOW!")

recording = sd.rec(
    int(duration * sample_rate),
    samplerate=sample_rate,
    channels=1,
    dtype=np.int16,
    device=device_id
)
sd.wait()

print(f"\nRecording complete!")
print(f"  Samples: {len(recording)}")
print(f"  Range: [{recording.min()}, {recording.max()}]")
print(f"  Mean: {recording.mean():.1f}")
print(f"  RMS: {np.sqrt(np.mean(recording.astype(np.float32) ** 2)):.1f}")

if abs(recording.max()) < 500:
    print("\n⚠️  WARNING: Audio levels very low! Check:")
    print("  - Microphone is not muted")
    print("  - Input volume/gain is turned up")
    print("  - Correct device is selected")
else:
    print("\n✓ Audio levels look good!")
