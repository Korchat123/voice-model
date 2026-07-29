"""Safe startup-configuration tests."""

import pytest

from voice_model.service.settings import ServiceSettings


def test_defaults_bind_only_to_loopback() -> None:
    assert ServiceSettings().host == "127.0.0.1"


def test_environment_surface_is_explicit_and_typed() -> None:
    settings = ServiceSettings.from_environment(
        {
            "VOICE_HOST": "127.0.0.2",
            "VOICE_PORT": "9000",
            "VOICE_MAX_CONCURRENT": "2",
            "VOICE_MAX_QUEUED": "3",
            "VOICE_REQUEST_TIMEOUT_MS": "4000",
            "UNRELATED_SECRET": "ignored",
        }
    )
    assert (settings.host, settings.port) == ("127.0.0.2", 9000)
    assert settings.max_concurrent_requests == 2
    assert settings.max_queued_requests == 3


@pytest.mark.parametrize(
    "environment",
    [
        {"VOICE_PORT": "not-a-number"},
        {"VOICE_MAX_CONCURRENT": "0"},
        {"VOICE_MAX_QUEUED": "-1"},
    ],
)
def test_invalid_environment_fails_closed(environment: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        ServiceSettings.from_environment(environment)
