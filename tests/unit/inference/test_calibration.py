from pathlib import Path

import pytest

from voice_model.domain import DomainError, ErrorCode
from voice_model.inference import (
    CalibrationSet,
    ControlMapping,
    load_calibration,
    load_presets,
)


def _mapping(
    control: str = "resonance",
    *,
    measured: bool = True,
    approved: bool = True,
    neutral_safe: bool = True,
) -> ControlMapping:
    return ControlMapping(
        control=control,
        engine_parameter=f"native_{control}",
        public_points=(-1.0, 0.0, 1.0),
        engine_points=(-0.25, 0.0, 0.25),
        engine_minimum=-0.3,
        engine_maximum=0.3,
        measured=measured,
        approved=approved,
        evidence_revision="report-sha256:abc",
        neutral_fallback_safe=neutral_safe,
    )


def _calibration(mapping: ControlMapping) -> CalibrationSet:
    return CalibrationSet(1, "1.0.0", "test-engine", "engine-sha", {mapping.control: mapping})


def test_resonance_interpolates_pinched_neutral_open_monotonically() -> None:
    mapping = _mapping()
    assert [mapping.interpolate(value) for value in (-1.0, -0.5, 0.0, 0.5, 1.0)] == [
        -0.25,
        -0.125,
        0.0,
        0.125,
        0.25,
    ]


def test_non_monotonic_mapping_is_rejected() -> None:
    with pytest.raises(ValueError, match="monotonic"):
        ControlMapping(
            control="pitch",
            engine_parameter="pitch",
            public_points=(-1.0, 0.0, 1.0),
            engine_points=(-0.2, 0.2, 0.1),
            engine_minimum=-1.0,
            engine_maximum=1.0,
            measured=False,
            approved=False,
            evidence_revision="UNSET",
            neutral_fallback_safe=False,
        )


def test_approval_requires_measurement_and_evidence() -> None:
    with pytest.raises(ValueError, match="measured immutable evidence"):
        _mapping(measured=False, approved=True)


def test_non_neutral_unapproved_mapping_fails_explicitly() -> None:
    calibration = _calibration(_mapping(measured=False, approved=False))
    with pytest.raises(DomainError) as raised:
        calibration.apply({"resonance": -0.5}, engine_capabilities=frozenset({"resonance"}))
    assert raised.value.code is ErrorCode.UNSUPPORTED_CAPABILITY


def test_neutral_fallback_is_omitted_only_when_declared_safe() -> None:
    safe = _calibration(_mapping(measured=False, approved=False, neutral_safe=True))
    assert safe.apply({"resonance": 0.0}, engine_capabilities=frozenset()) == {}

    unsafe = _calibration(_mapping(measured=False, approved=False, neutral_safe=False))
    with pytest.raises(DomainError):
        unsafe.apply({"resonance": 0.0}, engine_capabilities=frozenset())


def test_capability_filter_rejects_unsupported_non_neutral_control() -> None:
    with pytest.raises(DomainError) as raised:
        _calibration(_mapping()).apply(
            {"resonance": 0.5},
            engine_capabilities=frozenset({"pitch"}),
        )
    assert raised.value.details[0].field == "controls.resonance"


def test_preset_and_unapproved_example_configs_load() -> None:
    version, presets = load_presets(Path("configs/inference/presets.example.json"))
    calibration = load_calibration(Path("configs/inference/presets/control-mappings.example.toml"))
    assert version == "1.0.0"
    assert presets["neutral"].controls["resonance"] == 0.0
    assert calibration.mappings["resonance"].usable is False
