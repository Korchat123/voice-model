"""Versioned, bounded, approval-gated voice-control mappings."""

import json
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise
from math import isfinite
from pathlib import Path
from typing import Any, Final, NoReturn

from voice_model.domain import CONTROL_NAMES
from voice_model.domain.errors import DomainError, ErrorCode, ValidationDetail

_CONTROL_NAMES: Final = frozenset(CONTROL_NAMES)


@dataclass(frozen=True, slots=True)
class Preset:
    id: str
    version: str
    description: str
    controls: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class ControlMapping:
    control: str
    engine_parameter: str
    public_points: tuple[float, ...]
    engine_points: tuple[float, ...]
    engine_minimum: float
    engine_maximum: float
    measured: bool
    approved: bool
    evidence_revision: str
    neutral_fallback_safe: bool

    def __post_init__(self) -> None:
        if self.control not in _CONTROL_NAMES:
            raise ValueError(f"unknown public control: {self.control}")
        if len(self.public_points) < 3 or len(self.public_points) != len(self.engine_points):
            raise ValueError("mapping requires at least three aligned anchor points")
        if self.public_points != tuple(sorted(set(self.public_points))):
            raise ValueError("public anchor points must be unique and increasing")
        if self.public_points[0] != -1.0 or self.public_points[-1] != 1.0:
            raise ValueError("public anchor points must span -1.0 to 1.0")
        if 0.0 not in self.public_points:
            raise ValueError("mapping must define calibrated neutral at 0.0")
        if not all(isfinite(value) for value in self.engine_points):
            raise ValueError("engine anchor points must be finite")
        if (
            not self.engine_minimum
            <= min(self.engine_points)
            <= max(self.engine_points)
            <= self.engine_maximum
        ):
            raise ValueError("engine anchor points exceed configured bounds")
        increasing = all(left <= right for left, right in pairwise(self.engine_points))
        decreasing = all(left >= right for left, right in pairwise(self.engine_points))
        if not increasing and not decreasing:
            raise ValueError("engine anchor points must be monotonic")
        if self.approved and (not self.measured or self.evidence_revision.startswith("UNSET")):
            raise ValueError("approved mappings require measured immutable evidence")

    @property
    def usable(self) -> bool:
        return self.measured and self.approved

    def interpolate(self, public_value: float) -> float:
        if not isfinite(public_value) or not -1.0 <= public_value <= 1.0:
            raise ValueError("public control value must be finite and bounded")
        for index, right in enumerate(self.public_points[1:], 1):
            if public_value <= right:
                left = self.public_points[index - 1]
                engine_left = self.engine_points[index - 1]
                engine_right = self.engine_points[index]
                fraction = (public_value - left) / (right - left)
                value = engine_left + fraction * (engine_right - engine_left)
                return min(self.engine_maximum, max(self.engine_minimum, value))
        return self.engine_points[-1]


@dataclass(frozen=True, slots=True)
class CalibrationSet:
    schema_version: int
    calibration_version: str
    engine_id: str
    engine_revision: str
    mappings: Mapping[str, ControlMapping]

    def apply(
        self,
        public_controls: Mapping[str, float],
        *,
        engine_capabilities: frozenset[str],
    ) -> dict[str, float]:
        unknown = public_controls.keys() - _CONTROL_NAMES
        if unknown:
            raise DomainError(
                ErrorCode.UNKNOWN_CONTROL,
                *(
                    ValidationDetail(f"controls.{name}", "unknown control")
                    for name in sorted(unknown)
                ),
            )
        result: dict[str, float] = {}
        for name, public_value in public_controls.items():
            mapping = self.mappings.get(name)
            if name not in engine_capabilities:
                if public_value == 0.0 and mapping and mapping.neutral_fallback_safe:
                    continue
                self._unsupported(name, "control is unsupported by the active engine")
            if mapping is None:
                self._unsupported(name, "control has no calibrated mapping")
            if not mapping.usable:
                if public_value == 0.0 and mapping.neutral_fallback_safe:
                    continue
                self._unsupported(name, "control mapping is not measured and approved")
            result[mapping.engine_parameter] = mapping.interpolate(public_value)
        return result

    @staticmethod
    def _unsupported(name: str, reason: str) -> NoReturn:
        raise DomainError(
            ErrorCode.UNSUPPORTED_CAPABILITY,
            ValidationDetail(f"controls.{name}", reason),
        )


def load_presets(path: Path) -> tuple[str, dict[str, Preset]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("unsupported preset schema")
    collection_version = _text(payload, "collection_version")
    raw_presets = payload.get("presets")
    if not isinstance(raw_presets, list) or not raw_presets:
        raise ValueError("presets must be a non-empty array")
    presets: dict[str, Preset] = {}
    for raw in raw_presets:
        if not isinstance(raw, dict):
            raise ValueError("preset must be an object")
        identifier = _text(raw, "id")
        controls = raw.get("controls")
        if not isinstance(controls, dict):
            raise ValueError("preset controls must be an object")
        parsed = {
            name: _bounded(value, f"controls.{name}")
            for name, value in controls.items()
            if name in _CONTROL_NAMES
        }
        if len(parsed) != len(controls):
            raise ValueError("preset contains unknown controls")
        if identifier in presets:
            raise ValueError("preset IDs must be unique")
        presets[identifier] = Preset(
            identifier,
            _text(raw, "version"),
            _text(raw, "description"),
            parsed,
        )
    return collection_version, presets


def load_calibration(path: Path) -> CalibrationSet:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported calibration schema")
    raw_mappings = payload.get("mappings")
    if not isinstance(raw_mappings, list) or not raw_mappings:
        raise ValueError("mappings must be a non-empty array")
    mappings: dict[str, ControlMapping] = {}
    for raw in raw_mappings:
        if not isinstance(raw, dict):
            raise ValueError("mapping must be a table")
        control = _text(raw, "control")
        if control in mappings:
            raise ValueError("control mappings must be unique")
        mappings[control] = ControlMapping(
            control=control,
            engine_parameter=_text(raw, "engine_parameter"),
            public_points=_number_tuple(raw, "public_points"),
            engine_points=_number_tuple(raw, "engine_points"),
            engine_minimum=_number(raw, "engine_minimum"),
            engine_maximum=_number(raw, "engine_maximum"),
            measured=_boolean(raw, "measured"),
            approved=_boolean(raw, "approved"),
            evidence_revision=_text(raw, "evidence_revision"),
            neutral_fallback_safe=_boolean(raw, "neutral_fallback_safe"),
        )
    return CalibrationSet(
        schema_version=1,
        calibration_version=_text(payload, "calibration_version"),
        engine_id=_text(payload, "engine_id"),
        engine_revision=_text(payload, "engine_revision"),
        mappings=mappings,
    )


def _text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(f"{key} must be a non-empty string")
    return item


def _number(value: Mapping[str, Any], key: str) -> float:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, (int, float)) or not isfinite(item):
        raise ValueError(f"{key} must be a finite number")
    return float(item)


def _bounded(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    result = float(value)
    if not isfinite(result) or not -1.0 <= result <= 1.0:
        raise ValueError(f"{field} must be finite and in [-1.0, 1.0]")
    return result


def _number_tuple(value: Mapping[str, Any], key: str) -> tuple[float, ...]:
    items = value.get(key)
    if not isinstance(items, list):
        raise ValueError(f"{key} must be an array")
    return tuple(_bounded_number(item, key) for item in items)


def _bounded_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{field} values must be finite numbers")
    return float(value)


def _boolean(value: Mapping[str, Any], key: str) -> bool:
    item = value.get(key)
    if not isinstance(item, bool):
        raise ValueError(f"{key} must be a boolean")
    return item
