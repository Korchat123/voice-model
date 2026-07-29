"""Fail-closed registry for test and approved engine adapters."""

import json
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from voice_model.domain import SynthesisRequest
from voice_model.domain.errors import DomainError, ErrorCode, ValidationDetail
from voice_model.engines.base import AudioChunk, CancellationToken, Engine, EngineCapabilities

_CONTROL_NAMES: Final = frozenset(
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


class AdapterApproval(StrEnum):
    TEST_ONLY = "test-only"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ConfiguredModel:
    id: str
    version: str
    artifact_revision: str


@dataclass(frozen=True, slots=True)
class AdapterConfig:
    id: str
    factory: str
    approval: AdapterApproval
    model: ConfiguredModel
    languages: frozenset[str]
    controls: frozenset[str]
    supports_streaming: bool
    supports_timings: bool
    settings: Mapping[str, str | int | float | bool | None]


EngineFactory = Callable[[Mapping[str, str | int | float | bool | None]], Engine]


class CapabilityCheckedEngine:
    """Validate a request against reported capabilities before delegation."""

    def __init__(
        self,
        engine: Engine,
        *,
        exposed_controls: frozenset[str] | None = None,
    ) -> None:
        self._engine = engine
        runtime = engine.capabilities
        controls = runtime.controls if exposed_controls is None else exposed_controls
        if not controls <= runtime.controls:
            raise ValueError("exposed controls exceed runtime-reported controls")
        self._capabilities = EngineCapabilities(
            model_id=runtime.model_id,
            model_version=runtime.model_version,
            voices=runtime.voices,
            languages=runtime.languages,
            encodings=runtime.encodings,
            sample_rates_hz=runtime.sample_rates_hz,
            controls=controls,
            supports_timings=runtime.supports_timings,
        )

    @property
    def capabilities(self) -> EngineCapabilities:
        return self._capabilities

    def predict_duration_ms(self, request: SynthesisRequest) -> int:
        self._validate(request)
        return self._engine.predict_duration_ms(request)

    def synthesize(
        self, request: SynthesisRequest, cancellation: CancellationToken
    ) -> Iterator[AudioChunk]:
        self._validate(request)
        yield from self._engine.synthesize(request, cancellation)

    def _validate(self, request: SynthesisRequest) -> None:
        capabilities = self.capabilities
        if request.voice not in capabilities.voices:
            raise DomainError(
                ErrorCode.VOICE_NOT_FOUND,
                ValidationDetail("voice", "voice is unavailable"),
            )
        if request.language not in capabilities.languages:
            self._unsupported("language")
        if request.encoding not in capabilities.encodings:
            raise DomainError(
                ErrorCode.UNSUPPORTED_ENCODING,
                ValidationDetail("encoding", "encoding is unavailable"),
            )
        if request.sample_rate_hz not in capabilities.sample_rates_hz:
            raise DomainError(
                ErrorCode.UNSUPPORTED_ENCODING,
                ValidationDetail("sample_rate_hz", "sample rate is unavailable"),
            )
        if request.return_timings and not capabilities.supports_timings:
            self._unsupported("return_timings")
        requested = {name for name, value in request.controls.as_dict().items() if value != 0.0}
        unsupported = requested - capabilities.controls
        if unsupported:
            raise DomainError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                *(
                    ValidationDetail(f"controls.{name}", "control is unsupported by this engine")
                    for name in sorted(unsupported)
                ),
            )

    @staticmethod
    def _unsupported(field: str) -> None:
        raise DomainError(
            ErrorCode.UNSUPPORTED_CAPABILITY,
            ValidationDetail(field, "capability is unsupported by this engine"),
        )


class AdapterRegistry:
    """Resolve explicitly registered factories; never import config-provided code."""

    def __init__(self) -> None:
        self._factories: dict[str, EngineFactory] = {}

    def register(self, factory_path: str, factory: EngineFactory) -> None:
        if factory_path in self._factories:
            raise ValueError(f"adapter factory already registered: {factory_path}")
        self._factories[factory_path] = factory

    def create(
        self,
        config: AdapterConfig,
        *,
        allow_test_adapters: bool = False,
    ) -> CapabilityCheckedEngine:
        if config.approval is AdapterApproval.TEST_ONLY and not allow_test_adapters:
            raise PermissionError("test-only adapter requires explicit test mode")
        if config.approval not in {AdapterApproval.APPROVED, AdapterApproval.TEST_ONLY}:
            raise PermissionError(f"adapter is not approved: {config.approval}")
        try:
            factory = self._factories[config.factory]
        except KeyError:
            raise LookupError(f"adapter factory is not registered: {config.factory}") from None
        engine = factory(config.settings)
        capabilities = engine.capabilities
        if (capabilities.model_id, capabilities.model_version) != (
            config.model.id,
            config.model.version,
        ):
            raise RuntimeError("configured and runtime model identity do not match")
        if not config.controls <= capabilities.controls:
            raise RuntimeError("configured controls exceed runtime-reported controls")
        if config.supports_timings and not capabilities.supports_timings:
            raise RuntimeError("configured timing support exceeds runtime capability")
        runtime_languages = {language.value for language in capabilities.languages}
        if not config.languages <= runtime_languages:
            raise RuntimeError("configured languages exceed runtime-reported languages")
        return CapabilityCheckedEngine(engine, exposed_controls=config.controls)


def load_adapter_config(path: Path) -> tuple[str | None, tuple[AdapterConfig, ...]]:
    """Load the JSON registry format after strict structural checks."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("adapter configuration must be an object")
    allowed_top = {"$schema", "schema_version", "selected_adapter", "adapters"}
    _reject_unknown(payload, allowed_top, "configuration")
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported adapter configuration schema version")
    selected = payload.get("selected_adapter")
    if selected is not None and not isinstance(selected, str):
        raise ValueError("selected_adapter must be a string or null")
    raw_adapters = payload.get("adapters")
    if not isinstance(raw_adapters, list) or not raw_adapters:
        raise ValueError("adapters must be a non-empty array")
    adapters = tuple(_parse_adapter(item) for item in raw_adapters)
    ids = [adapter.id for adapter in adapters]
    if len(ids) != len(set(ids)):
        raise ValueError("adapter IDs must be unique")
    if selected is not None and selected not in ids:
        raise ValueError("selected adapter is not configured")
    return selected, adapters


def _parse_adapter(value: object) -> AdapterConfig:
    if not isinstance(value, dict):
        raise ValueError("adapter must be an object")
    allowed = {
        "id",
        "factory",
        "approval",
        "model",
        "languages",
        "controls",
        "supports_streaming",
        "supports_timings",
        "settings",
    }
    _reject_unknown(value, allowed, "adapter")
    required = allowed - {"settings"}
    if not required <= value.keys():
        raise ValueError("adapter is missing required fields")
    model = value["model"]
    if not isinstance(model, dict):
        raise ValueError("model must be an object")
    _reject_unknown(model, {"id", "version", "artifact_revision"}, "model")
    if set(model) != {"id", "version", "artifact_revision"}:
        raise ValueError("model identity fields are required")
    settings = value.get("settings", {})
    if not isinstance(settings, dict):
        raise ValueError("settings must be an object")
    forbidden = ("secret", "token", "password", "path", "file", "dir", "url")
    if any(any(word in key.lower() for word in forbidden) for key in settings):
        raise ValueError("adapter settings cannot contain secrets, URLs, or paths")
    languages = _string_set(value["languages"], "languages")
    controls = _string_set(value["controls"], "controls")
    if not controls <= _CONTROL_NAMES:
        raise ValueError("adapter contains an unknown control")
    return AdapterConfig(
        id=_string(value["id"], "id"),
        factory=_string(value["factory"], "factory"),
        approval=AdapterApproval(value["approval"]),
        model=ConfiguredModel(
            id=_string(model["id"], "model.id"),
            version=_string(model["version"], "model.version"),
            artifact_revision=_string(model["artifact_revision"], "model.artifact_revision"),
        ),
        languages=languages,
        controls=controls,
        supports_streaming=_boolean(value["supports_streaming"], "supports_streaming"),
        supports_timings=_boolean(value["supports_timings"], "supports_timings"),
        settings=settings,
    )


def _reject_unknown(value: Mapping[str, Any], allowed: set[str], subject: str) -> None:
    unknown = value.keys() - allowed
    if unknown:
        raise ValueError(f"{subject} has unknown fields: {', '.join(sorted(unknown))}")


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _string_set(value: object, field: str) -> frozenset[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be an array of strings")
    result = frozenset(value)
    if len(result) != len(value):
        raise ValueError(f"{field} must contain unique values")
    return result


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value
