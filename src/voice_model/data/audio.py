"""Conservative validation for uncompressed PCM WAV clips."""

from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AudioPolicy:
    sample_rate_hz: int = 24_000
    channels: int = 1
    sample_width_bytes: int = 2
    min_duration_seconds: float = 0.25
    max_duration_seconds: float = 30.0
    max_clipped_fraction: float = 0.0
    min_rms: int = 20


@dataclass(frozen=True, slots=True)
class AudioMetrics:
    sample_rate_hz: int
    channels: int
    sample_width_bytes: int
    frame_count: int
    duration_seconds: float
    peak: int
    rms: int
    clipped_fraction: float


DEFAULT_AUDIO_POLICY = AudioPolicy()


def inspect_wav(path: Path) -> AudioMetrics:
    """Inspect PCM WAV metadata and amplitude without decoding dependencies."""
    try:
        with wave.open(str(path), "rb") as wav:
            if wav.getcomptype() != "NONE":
                raise ValueError("compressed WAV is not supported")
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            frame_rate = wav.getframerate()
            frame_count = wav.getnframes()
            frames = wav.readframes(frame_count)
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"invalid WAV: {exc}") from exc
    if frame_rate <= 0 or sample_width not in {1, 2, 3, 4}:
        raise ValueError("invalid WAV sample format")
    full_scale = (1 << (sample_width * 8 - 1)) - 1
    squared_sum = 0
    peak = 0
    clipped = 0
    sample_count = frame_count * channels
    for offset in range(0, len(frames), sample_width):
        sample = frames[offset : offset + sample_width]
        if sample_width == 1:
            value = sample[0] - 128
        else:
            value = int.from_bytes(sample, "little", signed=True)
        magnitude = abs(value)
        peak = max(peak, magnitude)
        squared_sum += value * value
        clipped += magnitude >= full_scale
    rms = int((squared_sum / sample_count) ** 0.5) if sample_count else 0
    clipped_fraction = clipped / sample_count if sample_count else 0.0
    return AudioMetrics(
        sample_rate_hz=frame_rate,
        channels=channels,
        sample_width_bytes=sample_width,
        frame_count=frame_count,
        duration_seconds=frame_count / frame_rate,
        peak=peak,
        rms=rms,
        clipped_fraction=clipped_fraction,
    )


def validate_wav(
    path: Path, policy: AudioPolicy = DEFAULT_AUDIO_POLICY
) -> tuple[AudioMetrics, list[str]]:
    metrics = inspect_wav(path)
    errors: list[str] = []
    if metrics.sample_rate_hz != policy.sample_rate_hz:
        errors.append(
            f"sample_rate_hz must be {policy.sample_rate_hz}, got {metrics.sample_rate_hz}"
        )
    if metrics.channels != policy.channels:
        errors.append(f"channels must be {policy.channels}, got {metrics.channels}")
    if metrics.sample_width_bytes != policy.sample_width_bytes:
        errors.append(
            f"sample_width_bytes must be {policy.sample_width_bytes}, "
            f"got {metrics.sample_width_bytes}"
        )
    if not policy.min_duration_seconds <= metrics.duration_seconds <= policy.max_duration_seconds:
        errors.append(
            f"duration_seconds {metrics.duration_seconds:.3f} is outside "
            f"[{policy.min_duration_seconds}, {policy.max_duration_seconds}]"
        )
    if metrics.clipped_fraction > policy.max_clipped_fraction:
        errors.append(f"clipped_fraction {metrics.clipped_fraction:.6f} exceeds policy")
    if metrics.rms < policy.min_rms:
        errors.append(f"rms {metrics.rms} is below silence threshold {policy.min_rms}")
    return metrics, errors
