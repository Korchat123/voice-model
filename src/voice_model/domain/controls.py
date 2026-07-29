"""Bounded public voice controls."""

from collections.abc import Mapping
from dataclasses import dataclass, fields
from math import isfinite
from typing import ClassVar, Final

from voice_model.domain.errors import DomainError, ErrorCode, ValidationDetail

CONTROL_NAMES: Final = frozenset(
    {
        "pitch",
        "pace",
        "energy",
        "warmth",
        "brightness",
        "breathiness",
        "resonance",
        "expressiveness",
    }
)


@dataclass(frozen=True, slots=True)
class VoiceControls:
    """Resolved voice controls where zero is the calibrated neutral value."""

    minimum: ClassVar[float] = -1.0
    maximum: ClassVar[float] = 1.0

    pitch: float = 0.0
    pace: float = 0.0
    energy: float = 0.0
    warmth: float = 0.0
    brightness: float = 0.0
    breathiness: float = 0.0
    resonance: float = 0.0
    expressiveness: float = 0.0

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                self._raise_range(field.name)
            numeric = float(value)
            if not isfinite(numeric) or not self.minimum <= numeric <= self.maximum:
                self._raise_range(field.name)
            object.__setattr__(self, field.name, numeric)

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "VoiceControls":
        """Parse controls while rejecting unknown names."""

        unknown = values.keys() - CONTROL_NAMES
        if unknown:
            raise DomainError(
                ErrorCode.UNKNOWN_CONTROL,
                *(
                    ValidationDetail(f"controls.{name}", "unknown control")
                    for name in sorted(unknown)
                ),
            )
        return cls(**values)  # type: ignore[arg-type]

    def as_dict(self) -> dict[str, float]:
        """Return all resolved values using public field names."""

        return {field.name: getattr(self, field.name) for field in fields(self)}

    @staticmethod
    def _raise_range(name: str) -> None:
        raise DomainError(
            ErrorCode.CONTROL_OUT_OF_RANGE,
            ValidationDetail(f"controls.{name}", "must be a finite number between -1.0 and 1.0"),
        )
