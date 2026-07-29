"""Timing, cancellation, transcript, and control evaluation structures."""

from dataclasses import dataclass
from itertools import pairwise
from math import ceil
from statistics import median
from typing import TypeVar

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class LatencyMetrics:
    count: int
    first_audio_median_ms: float
    first_audio_p95_ms: float
    rtf_median: float
    rtf_p95: float

    @classmethod
    def from_samples(
        cls,
        first_audio_ms: list[float],
        synthesis_ms: list[float],
        audio_duration_ms: list[float],
    ) -> "LatencyMetrics":
        if not first_audio_ms or len(first_audio_ms) != len(synthesis_ms):
            raise ValueError("latency sample lists must be non-empty and aligned")
        if len(synthesis_ms) != len(audio_duration_ms) or any(
            duration <= 0 for duration in audio_duration_ms
        ):
            raise ValueError("audio durations must be positive and aligned")
        if any(value < 0 for value in first_audio_ms + synthesis_ms):
            raise ValueError("latencies cannot be negative")
        rtf = [
            synthesis / duration
            for synthesis, duration in zip(synthesis_ms, audio_duration_ms, strict=True)
        ]
        return cls(
            count=len(first_audio_ms),
            first_audio_median_ms=median(first_audio_ms),
            first_audio_p95_ms=_percentile(first_audio_ms, 0.95),
            rtf_median=median(rtf),
            rtf_p95=_percentile(rtf, 0.95),
        )


@dataclass(frozen=True, slots=True)
class CancellationMetrics:
    count: int
    median_ms: float
    p95_ms: float
    maximum_ms: float

    @classmethod
    def from_samples(cls, stop_latency_ms: list[float]) -> "CancellationMetrics":
        if not stop_latency_ms or any(value < 0 for value in stop_latency_ms):
            raise ValueError("cancellation samples must be non-empty and non-negative")
        return cls(
            count=len(stop_latency_ms),
            median_ms=median(stop_latency_ms),
            p95_ms=_percentile(stop_latency_ms, 0.95),
            maximum_ms=max(stop_latency_ms),
        )


@dataclass(frozen=True, slots=True)
class ControlMonotonicity:
    control: str
    levels: tuple[float, ...]
    observations: tuple[float, ...]
    direction: str
    monotonic: bool

    @classmethod
    def evaluate(
        cls,
        control: str,
        levels: list[float],
        observations: list[float],
        *,
        direction: str = "increasing",
        tolerance: float = 0.0,
    ) -> "ControlMonotonicity":
        if len(levels) < 3 or len(levels) != len(observations):
            raise ValueError("control evaluation requires at least three aligned samples")
        if levels != sorted(levels) or len(levels) != len(set(levels)):
            raise ValueError("control levels must be unique and increasing")
        if direction not in {"increasing", "decreasing"}:
            raise ValueError("direction must be increasing or decreasing")
        pairs = pairwise(observations)
        if direction == "increasing":
            passed = all(right + tolerance >= left for left, right in pairs)
        else:
            passed = all(right - tolerance <= left for left, right in pairs)
        return cls(control, tuple(levels), tuple(observations), direction, passed)


def error_rate(reference: list[_T], hypothesis: list[_T]) -> float:
    """Compute normalized edit distance after an external adapter transcribes audio."""

    if not reference:
        raise ValueError("reference tokens must not be empty")
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, 1):
        current = [row]
        for column, actual in enumerate(hypothesis, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (expected != actual),
                )
            )
        previous = current
    return previous[-1] / len(reference)


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, ceil(fraction * len(ordered)) - 1)]
