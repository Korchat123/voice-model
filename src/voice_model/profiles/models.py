"""Validated voice profile metadata. Audio bytes are never accepted."""

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from voice_model.domain.controls import CONTROL_NAMES

_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_SOURCES = frozenset({"licensed-synthetic", "designed-synthetic", "consented-recording"})
_LANGUAGES = frozenset({"th", "en", "mixed"})
_STYLES = frozenset({"neutral", "warm", "cheerful", "serious", "thinking", "custom"})
_REFERENCE_KEYS = frozenset({"filename", "media_type", "byte_size", "sha256", "note"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class VoiceProfile:
    profile_id: str
    display_name: str
    source: str
    language: str
    style: str
    controls: MappingProxyType[str, float]
    user_attested_right_to_use: bool
    signed_consent_record: str
    license_review: str
    reference: MappingProxyType[str, Any] | None
    training_approved: bool
    release_approved: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_setup_manifest(cls, payload: object) -> "VoiceProfile":
        if not isinstance(payload, dict):
            raise ValueError("body must be an object")
        allowed = {
            "schema_version",
            "status",
            "created_at",
            "voice",
            "authorization",
            "reference",
            "safety",
        }
        if unknown := set(payload) - allowed:
            raise ValueError(f"unknown top-level fields: {', '.join(sorted(unknown))}")
        if payload.get("schema_version") != "1.0":
            raise ValueError("schema_version must be 1.0")
        voice = _mapping(payload.get("voice"), "voice")
        authorization = _mapping(payload.get("authorization"), "authorization")
        safety = _mapping(payload.get("safety"), "safety")
        profile_id = _text(voice.get("id"), "voice.id", 64)
        if not _ID.fullmatch(profile_id):
            raise ValueError("voice.id must be a lowercase slug")
        display_name = _text(voice.get("display_name"), "voice.display_name", 80)
        source = _choice(voice.get("source"), "voice.source", _SOURCES)
        language = _choice(voice.get("language"), "voice.language", _LANGUAGES)
        style = _choice(voice.get("style"), "voice.style", _STYLES)
        controls = _controls(voice.get("controls"))
        attested = authorization.get("user_attested_right_to_use")
        if attested is not True:
            raise ValueError("voice authorization attestation is required")
        consent = _text(
            authorization.get("signed_consent_record", "USER_INPUT_REQUIRED"),
            "authorization.signed_consent_record",
            160,
        )
        license_review = _text(
            authorization.get("license_review", "USER_INPUT_REQUIRED"),
            "authorization.license_review",
            160,
        )
        reference = _reference(payload.get("reference"))
        training_approved = _strict_bool(
            safety.get("training_approved", False), "safety.training_approved"
        )
        release_approved = _strict_bool(
            safety.get("release_approved", False), "safety.release_approved"
        )
        now = datetime.now(UTC)
        return cls(
            profile_id=profile_id,
            display_name=display_name,
            source=source,
            language=language,
            style=style,
            controls=MappingProxyType(controls),
            user_attested_right_to_use=True,
            signed_consent_record=consent,
            license_review=license_review,
            reference=MappingProxyType(reference) if reference else None,
            training_approved=training_approved,
            release_approved=release_approved,
            created_at=now,
            updated_at=now,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "source": self.source,
            "language": self.language,
            "style": self.style,
            "controls": dict(self.controls),
            "authorization": {
                "user_attested_right_to_use": self.user_attested_right_to_use,
                "signed_consent_record": self.signed_consent_record,
                "license_review": self.license_review,
            },
            "reference": dict(self.reference) if self.reference else None,
            "safety": {
                "training_approved": self.training_approved,
                "release_approved": self.release_approved,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _text(value: object, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{field} must be non-empty text up to {maximum} characters")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{field} contains control characters")
    return value.strip()


def _choice(value: object, field: str, choices: frozenset[str]) -> str:
    text = _text(value, field, 64)
    if text not in choices:
        raise ValueError(f"{field} is unsupported")
    return text


def _controls(value: object) -> dict[str, float]:
    controls = _mapping(value, "voice.controls")
    if unknown := set(controls) - set(CONTROL_NAMES):
        raise ValueError(f"unknown voice controls: {', '.join(sorted(unknown))}")
    result: dict[str, float] = {}
    for name, raw in controls.items():
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"voice.controls.{name} must be a number")
        number = float(raw)
        if not math.isfinite(number) or not -1 <= number <= 1:
            raise ValueError(f"voice.controls.{name} must be between -1 and 1")
        result[name] = number
    return result


def _strict_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be true or false")
    return value


def _reference(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    reference = _mapping(value, "reference")
    if unknown := set(reference) - _REFERENCE_KEYS:
        raise ValueError(f"unknown reference fields: {', '.join(sorted(unknown))}")
    filename = _text(reference.get("filename"), "reference.filename", 180)
    if "/" in filename or "\\" in filename or filename in {".", ".."}:
        raise ValueError("reference.filename must be a basename")
    media_type = _text(reference.get("media_type"), "reference.media_type", 80)
    byte_size = reference.get("byte_size")
    if (
        isinstance(byte_size, bool)
        or not isinstance(byte_size, int)
        or not 0 < byte_size <= 100_000_000
    ):
        raise ValueError("reference.byte_size must be between 1 and 100000000")
    sha256 = _text(reference.get("sha256"), "reference.sha256", 64)
    if not _SHA256.fullmatch(sha256):
        raise ValueError("reference.sha256 must be lowercase SHA-256")
    return {
        "filename": filename,
        "media_type": media_type,
        "byte_size": byte_size,
        "sha256": sha256,
        "note": "Audio bytes are not stored in PostgreSQL.",
    }
