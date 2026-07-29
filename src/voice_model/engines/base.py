"""Engine boundary independent of any TTS vendor runtime."""

from collections.abc import Iterator
from dataclasses import dataclass
from threading import Event
from typing import Protocol

from voice_model.domain import AudioEncoding, Language, SynthesisRequest


@dataclass(frozen=True, slots=True)
class AudioChunk:
    """One bounded sequence of complete PCM frames."""

    pcm_s16le: bytes

    def __post_init__(self) -> None:
        if not self.pcm_s16le or len(self.pcm_s16le) % 2:
            raise ValueError("PCM chunks must contain complete 16-bit samples")


@dataclass(frozen=True, slots=True)
class EngineCapabilities:
    model_id: str
    model_version: str
    voices: frozenset[str]
    languages: frozenset[Language]
    encodings: frozenset[AudioEncoding]
    sample_rates_hz: frozenset[int]
    controls: frozenset[str]
    supports_timings: bool = False


class CancellationToken:
    """Thread-safe cooperative cancellation shared by all engine adapters."""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()


class Engine(Protocol):
    """Minimal contract implemented by fake and real synthesis engines."""

    @property
    def capabilities(self) -> EngineCapabilities: ...

    def predict_duration_ms(self, request: SynthesisRequest) -> int: ...

    def synthesize(
        self, request: SynthesisRequest, cancellation: CancellationToken
    ) -> Iterator[AudioChunk]: ...
