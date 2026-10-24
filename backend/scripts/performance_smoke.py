"""Reproducible CPU smoke measurements for local Vernis inference primitives."""

from __future__ import annotations

import json
import platform
import resource
import statistics
import time

import numpy as np
from PIL import Image

from app.services.computer_vision import perceptual_hash, visual_descriptor
from app.services.evidence import local_text_embedding


def _measure(callable_, iterations: int) -> dict[str, float | int]:
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        callable_()
        samples.append((time.perf_counter() - started) * 1000)
    ordered = sorted(samples)
    return {
        "iterations": iterations,
        "median_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[max(0, round(len(ordered) * 0.95) - 1)], 3),
        "max_ms": round(max(ordered), 3),
    }


def main() -> None:
    generator = np.random.default_rng(20261023)
    image = Image.fromarray(generator.integers(0, 256, (512, 512, 3), dtype=np.uint8), mode="RGB")
    text = "Owner supplied catalog record with a dated transfer, exhibition citation, and unresolved source gap. " * 16
    report = {
        "suite": "vernis-local-cpu-smoke-v1",
        "fixture": "deterministic synthetic data; not a domain-accuracy benchmark",
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor() or "not reported by operating system",
        },
        "measurements": {
            "visual_descriptor_512px": _measure(lambda: visual_descriptor(image), 100),
            "perceptual_hash_512px": _measure(lambda: perceptual_hash(image), 100),
            "text_embedding_1536d": _measure(lambda: local_text_embedding(text), 100),
        },
        "peak_process_rss_platform_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "limitations": [
            "Single-process smoke measurement with no concurrency or network traffic.",
            "Results cannot be extrapolated to production load or domain accuracy.",
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
