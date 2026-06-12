"""
Memory usage benchmarks for audio processing.

Uses tracemalloc to measure peak allocation during key operations.
These are unit-style tests that assert on memory bounds, not timed
via pytest-benchmark.

Run with:
    uv run pytest benchmarks/bench_memory.py -v
"""

from __future__ import annotations

import tracemalloc

import numpy as np


def _peak_kb(fn, *args, **kwargs) -> float:
    tracemalloc.start()
    fn(*args, **kwargs)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024


class TestMemoryBounds:
    def test_audio_buffer_1s_under_1mb(self) -> None:
        """1 second of float32 audio at 16 kHz should stay well under 1 MB."""

        def _make() -> np.ndarray:
            return np.zeros(16000, dtype=np.float32)

        peak_kb = _peak_kb(_make)
        assert peak_kb < 1024, f"Expected < 1024 KB, got {peak_kb:.1f} KB"

    def test_audio_buffer_60s_under_10mb(self) -> None:
        """60 seconds of float32 audio at 16 kHz: ~3.8 MB array."""

        def _make() -> np.ndarray:
            return np.zeros(16000 * 60, dtype=np.float32)

        peak_kb = _peak_kb(_make)
        assert peak_kb < 10 * 1024, f"Expected < 10 MB, got {peak_kb / 1024:.1f} MB"

    def test_chunk_concat_bounded(self) -> None:
        """Concatenating 100 chunks of 4096 samples each stays under 4 MB."""
        chunks = [np.zeros(4096, dtype=np.float32) for _ in range(100)]

        def _concat() -> np.ndarray:
            return np.concatenate(chunks)

        peak_kb = _peak_kb(_concat)
        assert peak_kb < 4 * 1024, f"Expected < 4 MB, got {peak_kb / 1024:.1f} MB"
