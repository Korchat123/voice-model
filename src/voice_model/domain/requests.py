"""Validated synthesis requests and resource limits."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, Never, cast

from voice_model.domain.controls import VoiceControls
from voice_model.domain.errors import DomainError, ErrorCode, ValidationDetail

_REQUEST_ID: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
_FIELDS: Final = frozenset(
    {
        "request_id",
        "text",
        "language",
        "voice",
        "preset",
        "controls",
        "seed",
        "encoding",
        "sample_rate_hz",
        "return_timings",
    }
)


class Language(StrEnum):
    THAI = "th"
    ENGLISH = "en"
    AUTO = "auto"


class AudioEncoding(StrEnum):
    PCM_S16LE = "pcm_s16le"
    WAV = "wav"


@dataclass(frozen=True, slots=True)
class RequestLimits:
    max_text_characters: int = 2_000
    max_utf8_bytes: int = 8_000
    max_predicted_audio_ms: int = 120_000

    def __post_init__(self) -> None:
        if min(self.max_text_characters, self.max_utf8_bytes, self.max_predicted_audio_ms) < 1:
            raise ValueError("request limits must be positive")


@dataclass(frozen=True, slots=True)
class SynthesisRequest:
    """A fully validated, transport-neutral synthesis request."""

    request_id: str
    text: str
    language: Language
    voice: str
    preset: str = "neutral"
    controls: VoiceControls = field(default_factory=VoiceControls)
    seed: int = 0
    encoding: AudioEncoding = AudioEncoding.PCM_S16LE
    sample_rate_hz: int = 24_000
    return_timings: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not _REQUEST_ID.fullmatch(self.request_id):
            self._invalid("request_id", "must match the public request ID format")
        if not isinstance(self.text, str) or not self.text.strip():
            self._invalid("text", "must contain non-whitespace text")
        if not isinstance(self.voice, str) or not self.voice or len(self.voice) > 64:
            self._invalid("voice", "must be a non-empty identifier of at most 64 characters")
        if not isinstance(self.preset, str) or not self.preset or len(self.preset) > 64:
            self._invalid("preset", "must be a non-empty identifier of at most 64 characters")
        if not isinstance(self.language, Language):
            self._unsupported("language")
        if not isinstance(self.encoding, AudioEncoding):
            raise DomainError(
                ErrorCode.UNSUPPORTED_ENCODING,
                ValidationDetail("encoding", "unsupported encoding"),
            )
        if not isinstance(self.controls, VoiceControls):
            self._invalid("controls", "must be resolved voice controls")
        if (
            isinstance(self.seed, bool)
            or not isinstance(self.seed, int)
            or not 0 <= self.seed <= 2**32 - 1
        ):
            self._invalid("seed", "must be an unsigned 32-bit integer")
        if self.sample_rate_hz != 24_000:
            raise DomainError(
                ErrorCode.UNSUPPORTED_ENCODING,
                ValidationDetail("sample_rate_hz", "unsupported sample rate"),
            )
        if not isinstance(self.return_timings, bool):
            self._invalid("return_timings", "must be a boolean")

    @classmethod
    def from_mapping(
        cls, values: Mapping[str, object], *, limits: RequestLimits | None = None
    ) -> "SynthesisRequest":
        """Parse an untrusted mapping, rejecting unknown and over-limit fields."""

        limits = limits or RequestLimits()
        unknown = values.keys() - _FIELDS
        if unknown:
            raise DomainError(
                ErrorCode.INVALID_REQUEST,
                *(ValidationDetail(name, "unknown field") for name in sorted(unknown)),
            )
        for required in ("request_id", "text", "language", "voice"):
            if required not in values:
                raise DomainError(
                    ErrorCode.INVALID_REQUEST,
                    ValidationDetail(required, "required field is missing"),
                )
        text = values["text"]
        if isinstance(text, str):
            if len(text) > limits.max_text_characters:
                cls._limit("text", "exceeds character limit")
            if len(text.encode("utf-8")) > limits.max_utf8_bytes:
                cls._limit("text", "exceeds UTF-8 byte limit")
        controls_value = values.get("controls", {})
        if not isinstance(controls_value, Mapping):
            cls._invalid("controls", "must be an object")
        try:
            language = Language(values["language"])  # type: ignore[arg-type]
        except (TypeError, ValueError):
            cls._unsupported("language")
        try:
            encoding = AudioEncoding(cast(str, values.get("encoding", AudioEncoding.PCM_S16LE)))
        except (TypeError, ValueError):
            raise DomainError(
                ErrorCode.UNSUPPORTED_ENCODING,
                ValidationDetail("encoding", "unsupported encoding"),
            ) from None
        return cls(
            request_id=values["request_id"],  # type: ignore[arg-type]
            text=text,  # type: ignore[arg-type]
            language=language,
            voice=values["voice"],  # type: ignore[arg-type]
            preset=values.get("preset", "neutral"),  # type: ignore[arg-type]
            controls=VoiceControls.from_mapping(cast(Mapping[str, object], controls_value)),
            seed=values.get("seed", 0),  # type: ignore[arg-type]
            encoding=encoding,
            sample_rate_hz=values.get("sample_rate_hz", 24_000),  # type: ignore[arg-type]
            return_timings=values.get("return_timings", False),  # type: ignore[arg-type]
        )

    def validate_limits(self, limits: RequestLimits, *, predicted_audio_ms: int) -> None:
        """Recheck limits after an engine supplies its bounded duration estimate."""

        if len(self.text) > limits.max_text_characters:
            self._limit("text", "exceeds character limit")
        if len(self.text.encode("utf-8")) > limits.max_utf8_bytes:
            self._limit("text", "exceeds UTF-8 byte limit")
        if predicted_audio_ms > limits.max_predicted_audio_ms:
            self._limit("text", "predicted audio exceeds duration limit")

    @staticmethod
    def _invalid(field: str, reason: str) -> Never:
        raise DomainError(ErrorCode.INVALID_REQUEST, ValidationDetail(field, reason))

    @staticmethod
    def _unsupported(field: str) -> Never:
        raise DomainError(
            ErrorCode.UNSUPPORTED_CAPABILITY,
            ValidationDetail(field, "unsupported capability"),
        )

    @staticmethod
    def _limit(field: str, reason: str) -> Never:
        raise DomainError(ErrorCode.LIMIT_EXCEEDED, ValidationDetail(field, reason))
