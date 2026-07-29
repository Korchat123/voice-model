"""Synthesis-request validation tests."""

import pytest

from voice_model.domain import DomainError, ErrorCode, RequestLimits, SynthesisRequest


def request(**updates: object) -> dict[str, object]:
    values: dict[str, object] = {
        "request_id": "turn-1",
        "text": "Hello สวัสดี",
        "language": "auto",
        "voice": "primary",
    }
    values.update(updates)
    return values


def test_minimal_request_resolves_defaults() -> None:
    parsed = SynthesisRequest.from_mapping(request())
    assert parsed.preset == "neutral"
    assert parsed.seed == 0
    assert parsed.controls.resonance == 0.0


@pytest.mark.parametrize(
    ("updates", "code"),
    [
        ({"unexpected": 1}, ErrorCode.INVALID_REQUEST),
        ({"request_id": "../audio"}, ErrorCode.INVALID_REQUEST),
        ({"text": "   "}, ErrorCode.INVALID_REQUEST),
        ({"language": "fr"}, ErrorCode.UNSUPPORTED_CAPABILITY),
        ({"encoding": "mp3"}, ErrorCode.UNSUPPORTED_ENCODING),
        ({"sample_rate_hz": 48_000}, ErrorCode.UNSUPPORTED_ENCODING),
        ({"seed": -1}, ErrorCode.INVALID_REQUEST),
        ({"seed": 2**32}, ErrorCode.INVALID_REQUEST),
    ],
)
def test_invalid_request_fields_have_stable_codes(
    updates: dict[str, object], code: ErrorCode
) -> None:
    with pytest.raises(DomainError) as raised:
        SynthesisRequest.from_mapping(request(**updates))
    assert raised.value.code is code


def test_character_and_utf8_byte_limits_are_independent() -> None:
    limits = RequestLimits(max_text_characters=4, max_utf8_bytes=4)
    with pytest.raises(DomainError) as characters:
        SynthesisRequest.from_mapping(request(text="abcde"), limits=limits)
    assert characters.value.code is ErrorCode.LIMIT_EXCEEDED

    with pytest.raises(DomainError) as encoded:
        SynthesisRequest.from_mapping(request(text="กก"), limits=limits)
    assert encoded.value.code is ErrorCode.LIMIT_EXCEEDED


def test_predicted_duration_limit_is_enforced() -> None:
    parsed = SynthesisRequest.from_mapping(request())
    with pytest.raises(DomainError) as raised:
        parsed.validate_limits(RequestLimits(max_predicted_audio_ms=10), predicted_audio_ms=11)
    assert raised.value.code is ErrorCode.LIMIT_EXCEEDED


def test_missing_required_field_is_rejected() -> None:
    values = request()
    del values["voice"]
    with pytest.raises(DomainError) as raised:
        SynthesisRequest.from_mapping(values)
    assert raised.value.details[0].field == "voice"
