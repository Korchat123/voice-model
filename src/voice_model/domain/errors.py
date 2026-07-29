"""Stable, privacy-safe domain errors."""

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    """Error identifiers shared by transports."""

    INVALID_REQUEST = "INVALID_REQUEST"
    UNKNOWN_CONTROL = "UNKNOWN_CONTROL"
    CONTROL_OUT_OF_RANGE = "CONTROL_OUT_OF_RANGE"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    VOICE_NOT_FOUND = "VOICE_NOT_FOUND"
    UNSUPPORTED_ENCODING = "UNSUPPORTED_ENCODING"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"


@dataclass(frozen=True, slots=True)
class ValidationDetail:
    """A field-level reason that never contains the rejected value."""

    field: str
    reason: str


class DomainError(ValueError):
    """Expected invalid-input or unsupported-capability failure."""

    def __init__(self, code: ErrorCode, *details: ValidationDetail) -> None:
        super().__init__("A request field is invalid.")
        self.code = code
        self.details = details
