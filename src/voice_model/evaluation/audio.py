"""Deterministic PCM WAV quality measurements using the standard library."""

import wave
from dataclasses import asdict, dataclass
from math import log10, sqrt
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AudioMetrics:
    sample_rate_hz: int
    channels: int
    frames: int
    duration_ms: float
    peak_dbfs: float
    rms_dbfs: float
    clipped_samples: int
    silence_ratio: float

    def as_dict(self) -> dict[str, int | float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class IntelligibilityProxy:
    """Transcript-free duration/voicing sanity signal, not an intelligibility score."""

    normalized_character_count: int
    characters_per_second: float
    voiced_ms_per_character: float


def intelligibility_proxy(text: str, audio: AudioMetrics) -> IntelligibilityProxy:
    """Flag gross truncation/rate anomalies without pretending to replace ASR."""

    character_count = sum(not character.isspace() for character in text)
    if character_count < 1 or audio.duration_ms <= 0:
        raise ValueError("proxy requires non-whitespace text and positive-duration audio")
    voiced_ms = audio.duration_ms * (1 - audio.silence_ratio)
    return IntelligibilityProxy(
        normalized_character_count=character_count,
        characters_per_second=character_count / (audio.duration_ms / 1000),
        voiced_ms_per_character=voiced_ms / character_count,
    )


def measure_wav(path: Path, *, silence_dbfs: float = -50.0) -> AudioMetrics:
    """Measure uncompressed 16-bit PCM WAV without retaining the whole file."""

    total_samples = 0
    squared_sum = 0
    peak = 0
    clipped = 0
    silent = 0
    silence_amplitude = 32767 * (10 ** (silence_dbfs / 20))
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        sample_rate = source.getframerate()
        frames = source.getnframes()
        if source.getsampwidth() != 2 or source.getcomptype() != "NONE":
            raise ValueError("only uncompressed signed 16-bit PCM WAV is supported")
        if channels < 1 or sample_rate < 1:
            raise ValueError("invalid WAV audio format")
        while payload := source.readframes(4096):
            for offset in range(0, len(payload), 2):
                sample = int.from_bytes(payload[offset : offset + 2], "little", signed=True)
                magnitude = abs(sample)
                total_samples += 1
                squared_sum += sample * sample
                peak = max(peak, magnitude)
                clipped += int(sample in {-32768, 32767})
                silent += int(magnitude <= silence_amplitude)
    if total_samples == 0:
        raise ValueError("WAV contains no audio samples")
    rms = sqrt(squared_sum / total_samples)
    return AudioMetrics(
        sample_rate_hz=sample_rate,
        channels=channels,
        frames=frames,
        duration_ms=frames * 1000 / sample_rate,
        peak_dbfs=_dbfs(peak),
        rms_dbfs=_dbfs(rms),
        clipped_samples=clipped,
        silence_ratio=silent / total_samples,
    )


def _dbfs(amplitude: float) -> float:
    return -120.0 if amplitude <= 0 else 20 * log10(amplitude / 32767)
