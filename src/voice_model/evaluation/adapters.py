"""Interfaces for optional, separately approved evaluation dependencies."""

from typing import Protocol


class TranscriptionAdapter(Protocol):
    """External ASR boundary; implementations must document model provenance."""

    @property
    def adapter_id(self) -> str: ...

    @property
    def model_revision(self) -> str: ...

    def transcribe(self, audio_path: str, *, language: str) -> str: ...


class SpeakerMetricAdapter(Protocol):
    """External speaker-metric boundary; similarity is never a sole quality gate."""

    @property
    def adapter_id(self) -> str: ...

    @property
    def model_revision(self) -> str: ...

    def score(self, reference_path: str, generated_path: str) -> float: ...


def unavailable_reason(metric: str) -> str:
    return (
        f"{metric} was not measured: no approved external adapter and immutable "
        "model revision were supplied"
    )
