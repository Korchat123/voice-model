"""Terminal synthesis-metadata validation tests."""

import pytest

from voice_model.domain import SynthesisMetadata, VoiceControls


def metadata(**updates: object) -> SynthesisMetadata:
    values: dict[str, object] = {
        "request_id": "turn-1",
        "model_id": "fake-local",
        "model_version": "1",
        "runtime_version": "0.1.0",
        "sample_rate_hz": 24_000,
        "duration_ms": 10,
        "applied_controls": VoiceControls(),
        "completed": True,
    }
    values.update(updates)
    return SynthesisMetadata(**values)  # type: ignore[arg-type]


def test_valid_metadata_is_immutable() -> None:
    result = metadata()
    assert result.completed
    with pytest.raises(AttributeError):
        result.duration_ms = 20  # type: ignore[misc]


@pytest.mark.parametrize(
    "updates",
    [
        {"model_id": ""},
        {"duration_ms": -1},
        {"sample_rate_hz": 0},
        {"completed": True, "cancelled": True},
    ],
)
def test_inconsistent_metadata_is_rejected(updates: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        metadata(**updates)
