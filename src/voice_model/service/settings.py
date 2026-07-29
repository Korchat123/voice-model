"""Validated service configuration with safe local defaults."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from voice_model.domain import RequestLimits


@dataclass(frozen=True, slots=True)
class ServiceSettings:
    host: str = "127.0.0.1"
    port: int = 8080
    max_concurrent_requests: int = 1
    max_queued_requests: int = 2
    request_timeout_ms: int = 130_000
    tombstone_limit: int = 1_024
    request_limits: RequestLimits = field(default_factory=RequestLimits)

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("host must not be empty")
        values = (
            self.port,
            self.max_concurrent_requests,
            self.request_timeout_ms,
            self.tombstone_limit,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in values
        ):
            raise ValueError("service limits and port must be positive integers")
        if not isinstance(self.max_queued_requests, int) or self.max_queued_requests < 0:
            raise ValueError("max_queued_requests must be a non-negative integer")
        if self.port > 65_535:
            raise ValueError("port must be at most 65535")

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "ServiceSettings":
        """Load a deliberately small, non-secret environment surface."""

        source = os.environ if environment is None else environment
        return cls(
            host=source.get("VOICE_HOST", "127.0.0.1"),
            port=_integer(source, "VOICE_PORT", 8080),
            max_concurrent_requests=_integer(source, "VOICE_MAX_CONCURRENT", 1),
            max_queued_requests=_integer(source, "VOICE_MAX_QUEUED", 2),
            request_timeout_ms=_integer(source, "VOICE_REQUEST_TIMEOUT_MS", 130_000),
        )


def _integer(source: Mapping[str, str], name: str, default: int) -> int:
    raw = source.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None
