"""Deterministic, bounded PCM engine for unit and contract tests."""

from collections.abc import Iterator
from hashlib import sha256

from voice_model.domain import (
    CONTROL_NAMES,
    AudioEncoding,
    DomainError,
    ErrorCode,
    Language,
    SynthesisRequest,
    ValidationDetail,
)
from voice_model.engines.base import AudioChunk, CancellationToken, EngineCapabilities


class FakeEngine:
    """Emit deterministic pseudo-audio without model or audio dependencies."""

    def __init__(self, *, chunk_frames: int = 240, frames_per_character: int = 120) -> None:
        if chunk_frames < 1 or frames_per_character < 1:
            raise ValueError("fake-engine frame counts must be positive")
        self._chunk_frames = chunk_frames
        self._frames_per_character = frames_per_character
        self._capabilities = EngineCapabilities(
            model_id="fake-local",
            model_version="1",
            voices=frozenset({"primary"}),
            languages=frozenset(Language),
            encodings=frozenset({AudioEncoding.PCM_S16LE}),
            sample_rates_hz=frozenset({24_000}),
            controls=CONTROL_NAMES,
        )

    @property
    def capabilities(self) -> EngineCapabilities:
        return self._capabilities

    def predict_duration_ms(self, request: SynthesisRequest) -> int:
        frames = max(1, len(request.text)) * self._frames_per_character
        return (frames * 1_000 + request.sample_rate_hz - 1) // request.sample_rate_hz

    def synthesize(
        self, request: SynthesisRequest, cancellation: CancellationToken
    ) -> Iterator[AudioChunk]:
        if request.voice not in self.capabilities.voices:
            raise DomainError(
                ErrorCode.VOICE_NOT_FOUND,
                ValidationDetail("voice", "voice is unavailable"),
            )
        remaining = max(1, len(request.text)) * self._frames_per_character
        state = self._seed(request)
        while remaining and not cancellation.is_cancelled:
            frame_count = min(remaining, self._chunk_frames)
            output = bytearray(frame_count * 2)
            for offset in range(0, len(output), 2):
                state = (1_664_525 * state + 1_013_904_223) & 0xFFFFFFFF
                sample = ((state >> 16) & 0x1FFF) - 0x1000
                output[offset : offset + 2] = sample.to_bytes(2, "little", signed=True)
            yield AudioChunk(bytes(output))
            remaining -= frame_count

    @staticmethod
    def _seed(request: SynthesisRequest) -> int:
        controls = ",".join(
            f"{name}={value:.6f}" for name, value in request.controls.as_dict().items()
        )
        identity = (
            f"{request.text}\0{request.language}\0{request.voice}\0"
            f"{request.preset}\0{request.seed}\0{controls}"
        )
        return int.from_bytes(sha256(identity.encode("utf-8")).digest()[:4], "little")
