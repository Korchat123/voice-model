"""JSON projection helpers for transport-neutral domain objects."""

from typing import Any

from voice_model.domain import DomainError
from voice_model.engines import EngineCapabilities
from voice_model.service.settings import ServiceSettings


def error_body(error: DomainError, request_id: str | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": error.code.value,
            "message": str(error),
            "request_id": request_id,
            "details": [
                {"field": detail.field, "reason": detail.reason} for detail in error.details
            ],
            "retryable": False,
        }
    }


def capabilities_body(
    capabilities: EngineCapabilities, settings: ServiceSettings
) -> dict[str, Any]:
    return {
        "api_version": "v1",
        "runtime_version": "0.1.0",
        "model": {"id": capabilities.model_id, "version": capabilities.model_version},
        "voices": sorted(capabilities.voices),
        "languages": sorted(language.value for language in capabilities.languages),
        "encodings": sorted(encoding.value for encoding in capabilities.encodings),
        "streaming_encodings": ["pcm_s16le"],
        "sample_rates_hz": sorted(capabilities.sample_rates_hz),
        "controls": {
            name: {"minimum": -1.0, "maximum": 1.0, "default": 0.0}
            for name in sorted(capabilities.controls)
        },
        "presets": [{"id": "neutral", "version": "1.0.0"}],
        "limits": {
            "max_text_characters": settings.request_limits.max_text_characters,
            "max_utf8_bytes": settings.request_limits.max_utf8_bytes,
            "max_predicted_audio_ms": settings.request_limits.max_predicted_audio_ms,
            "request_timeout_ms": settings.request_timeout_ms,
            "max_concurrent_requests": settings.max_concurrent_requests,
            "max_queued_requests": settings.max_queued_requests,
            "cancel_target_ms": 250,
        },
        "timings": {
            "phonemes": capabilities.supports_timings,
            "visemes": capabilities.supports_timings,
        },
    }
