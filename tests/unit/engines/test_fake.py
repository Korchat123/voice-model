"""Deterministic fake-engine contract tests."""

import pytest

from voice_model.domain import DomainError, ErrorCode, SynthesisRequest
from voice_model.engines import AudioChunk, CancellationToken, Engine
from voice_model.engines.fake import FakeEngine


def request(*, text: str = "hello", seed: int = 7) -> SynthesisRequest:
    return SynthesisRequest.from_mapping(
        {
            "request_id": "fake-1",
            "text": text,
            "language": "en",
            "voice": "primary",
            "seed": seed,
        }
    )


def render(engine: Engine, synthesis_request: SynthesisRequest) -> bytes:
    return b"".join(
        chunk.pcm_s16le for chunk in engine.synthesize(synthesis_request, CancellationToken())
    )


def test_fake_engine_satisfies_protocol_and_emits_bounded_pcm() -> None:
    engine: Engine = FakeEngine(chunk_frames=8, frames_per_character=10)
    chunks = list(engine.synthesize(request(), CancellationToken()))
    assert chunks
    assert all(0 < len(chunk.pcm_s16le) <= 16 for chunk in chunks)
    assert all(len(chunk.pcm_s16le) % 2 == 0 for chunk in chunks)
    assert sum(len(chunk.pcm_s16le) for chunk in chunks) == 5 * 10 * 2


def test_output_is_deterministic_and_seed_sensitive() -> None:
    engine = FakeEngine()
    assert render(engine, request(seed=1)) == render(engine, request(seed=1))
    assert render(engine, request(seed=1)) != render(engine, request(seed=2))


def test_cancellation_stops_before_next_bounded_chunk() -> None:
    engine = FakeEngine(chunk_frames=4, frames_per_character=20)
    cancellation = CancellationToken()
    stream = engine.synthesize(request(), cancellation)
    first = next(stream)
    cancellation.cancel()
    assert first.pcm_s16le
    assert list(stream) == []
    assert cancellation.is_cancelled


def test_pre_cancelled_request_emits_nothing() -> None:
    cancellation = CancellationToken()
    cancellation.cancel()
    assert list(FakeEngine().synthesize(request(), cancellation)) == []


def test_duration_prediction_rounds_up_to_milliseconds() -> None:
    engine = FakeEngine(frames_per_character=1)
    assert engine.predict_duration_ms(request(text="a")) == 1


@pytest.mark.parametrize("payload", [b"", b"\x00"])
def test_audio_chunk_rejects_empty_or_partial_frames(payload: bytes) -> None:
    with pytest.raises(ValueError, match="complete 16-bit"):
        AudioChunk(payload)


def test_invalid_engine_configuration_is_rejected() -> None:
    with pytest.raises(ValueError):
        FakeEngine(chunk_frames=0)


def test_unavailable_voice_is_not_silently_ignored() -> None:
    unavailable = SynthesisRequest.from_mapping(
        {
            "request_id": "fake-2",
            "text": "hello",
            "language": "en",
            "voice": "missing",
        }
    )
    with pytest.raises(DomainError) as raised:
        list(FakeEngine().synthesize(unavailable, CancellationToken()))
    assert raised.value.code is ErrorCode.VOICE_NOT_FOUND
