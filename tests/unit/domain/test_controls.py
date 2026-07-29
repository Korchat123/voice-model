"""Voice-control validation tests."""

import math

import pytest

from voice_model.domain import DomainError, ErrorCode, VoiceControls


@pytest.mark.parametrize("value", [-1.0, 0.0, 1.0])
def test_control_boundaries_are_accepted(value: float) -> None:
    assert VoiceControls(resonance=value).resonance == value


@pytest.mark.parametrize("value", [-1.01, 1.01, math.inf, math.nan, True, "0.2"])
def test_invalid_control_values_are_rejected_without_echo(value: object) -> None:
    with pytest.raises(DomainError) as raised:
        VoiceControls.from_mapping({"resonance": value})
    assert raised.value.code is ErrorCode.CONTROL_OUT_OF_RANGE
    assert repr(value) not in str(raised.value)


def test_unknown_control_is_rejected() -> None:
    with pytest.raises(DomainError) as raised:
        VoiceControls.from_mapping({"nasality": 0.2})
    assert raised.value.code is ErrorCode.UNKNOWN_CONTROL
    assert raised.value.details[0].field == "controls.nasality"


def test_controls_are_resolved_to_all_public_names() -> None:
    values = VoiceControls(pace=0.25).as_dict()
    assert values["pace"] == 0.25
    assert len(values) == 8
