from pathlib import Path

import pytest

from voice_model.domain import DomainError, ErrorCode, Language, SynthesisRequest, VoiceControls
from voice_model.engines.adapters import (
    AdapterApproval,
    AdapterConfig,
    AdapterRegistry,
    CapabilityCheckedEngine,
    ConfiguredModel,
    load_adapter_config,
)
from voice_model.engines.adapters.testing import create_deterministic_test_adapter
from voice_model.engines.base import CancellationToken


def _config(**changes: object) -> AdapterConfig:
    values: dict[str, object] = {
        "id": "deterministic-test",
        "factory": ("voice_model.engines.adapters.testing:create_deterministic_test_adapter"),
        "approval": AdapterApproval.TEST_ONLY,
        "model": ConfiguredModel("fake-local", "1", "embedded-fixture-v1"),
        "languages": frozenset({"th", "en", "auto"}),
        "controls": frozenset({"pitch", "pace"}),
        "supports_streaming": True,
        "supports_timings": False,
        "settings": {"chunk_samples": 120},
    }
    values.update(changes)
    return AdapterConfig(**values)  # type: ignore[arg-type]


def _request(*, controls: VoiceControls | None = None) -> SynthesisRequest:
    return SynthesisRequest(
        request_id="adapter-test",
        text="ทดสอบ test",
        language=Language.AUTO,
        voice="primary",
        controls=controls or VoiceControls(),
    )


def _registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(
        "voice_model.engines.adapters.testing:create_deterministic_test_adapter",
        create_deterministic_test_adapter,
    )
    return registry


def test_example_config_loads_with_identity_and_approval() -> None:
    selected, adapters = load_adapter_config(
        Path("configs/inference/engines/adapters.example.json")
    )

    assert selected == "deterministic-test"
    assert adapters[0].model == ConfiguredModel("fake-local", "1", "embedded-fixture-v1")
    assert adapters[1].approval is AdapterApproval.PENDING


def test_pending_and_implicit_test_adapter_use_fail_closed() -> None:
    registry = _registry()

    with pytest.raises(PermissionError, match="explicit test mode"):
        registry.create(_config())
    with pytest.raises(PermissionError, match="not approved"):
        registry.create(_config(approval=AdapterApproval.PENDING))


def test_runtime_model_identity_must_match_config() -> None:
    with pytest.raises(RuntimeError, match="model identity"):
        _registry().create(
            _config(model=ConfiguredModel("wrong-model", "1", "embedded-fixture-v1")),
            allow_test_adapters=True,
        )


def test_supported_test_adapter_streams_when_identity_matches() -> None:
    engine = _registry().create(
        _config(model=ConfiguredModel("fake-local", "1", "embedded-fixture-v1")),
        allow_test_adapters=True,
    )

    chunks = list(engine.synthesize(_request(), CancellationToken()))

    assert chunks
    assert all(len(chunk.pcm_s16le) <= 240 for chunk in chunks)
    assert engine.capabilities.model_id == "fake-local"
    assert engine.capabilities.model_version == "1"


def test_non_neutral_unsupported_control_is_explicit_error() -> None:
    engine: CapabilityCheckedEngine = _registry().create(
        _config(
            model=ConfiguredModel("fake-local", "1", "embedded-fixture-v1"),
            controls=frozenset({"pitch", "pace"}),
        ),
        allow_test_adapters=True,
    )

    with pytest.raises(DomainError) as raised:
        engine.predict_duration_ms(_request(controls=VoiceControls(resonance=-0.5)))

    assert raised.value.code is ErrorCode.UNSUPPORTED_CAPABILITY
    assert raised.value.details[0].field == "controls.resonance"


def test_timing_request_is_rejected_when_not_supported() -> None:
    engine = _registry().create(
        _config(model=ConfiguredModel("fake-local", "1", "embedded-fixture-v1")),
        allow_test_adapters=True,
    )
    request = SynthesisRequest(
        request_id="timing-test",
        text="test",
        language=Language.ENGLISH,
        voice="primary",
        return_timings=True,
    )

    with pytest.raises(DomainError) as raised:
        engine.predict_duration_ms(request)

    assert raised.value.code is ErrorCode.UNSUPPORTED_CAPABILITY


def test_unknown_factory_is_never_imported_from_configuration() -> None:
    with pytest.raises(LookupError, match="not registered"):
        AdapterRegistry().create(
            _config(
                factory="voice_model.engines.adapters.testing:unknown",
                approval=AdapterApproval.APPROVED,
            )
        )
