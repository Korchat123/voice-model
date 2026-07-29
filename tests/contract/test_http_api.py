"""Public HTTP contract tests using the deterministic fake engine."""

from starlette.testclient import TestClient

from voice_model.domain import RequestLimits
from voice_model.engines.fake import FakeEngine
from voice_model.service import create_app
from voice_model.service.settings import ServiceSettings


def valid_request(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "request_id": "turn-1",
        "text": "hello",
        "language": "en",
        "voice": "primary",
    }
    value.update(updates)
    return value


def client(**settings: object) -> TestClient:
    return TestClient(
        create_app(
            engine=FakeEngine(chunk_frames=4, frames_per_character=2),
            settings=ServiceSettings(**settings),  # type: ignore[arg-type]
        )
    )


def test_health_and_capabilities_are_versioned() -> None:
    with client() as api:
        health = api.get("/v1/health")
        capabilities = api.get("/v1/capabilities")
    assert health.json() == {
        "status": "ok",
        "ready": True,
        "runtime_version": "0.1.0",
        "model_loaded": True,
    }
    assert capabilities.json()["api_version"] == "v1"
    assert capabilities.json()["model"] == {"id": "fake-local", "version": "1"}
    assert capabilities.json()["limits"]["max_concurrent_requests"] == 1


def test_synthesis_streams_complete_pcm_and_identity_headers() -> None:
    with client() as api:
        response = api.post(
            "/v1/synthesis",
            headers={"X-Request-ID": "turn-1"},
            json=valid_request(),
        )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "turn-1"
    assert response.headers["x-model-id"] == "fake-local"
    assert response.headers["x-audio-encoding"] == "pcm_s16le"
    assert len(response.content) == len("hello") * 2 * 2
    assert len(response.content) % 2 == 0


def test_request_id_header_must_match_body() -> None:
    with client() as api:
        response = api.post(
            "/v1/synthesis",
            headers={"X-Request-ID": "different"},
            json=valid_request(),
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_unsupported_engine_features_fail_instead_of_degrading() -> None:
    with client() as api:
        wav = api.post("/v1/synthesis", json=valid_request(encoding="wav"))
        timings = api.post("/v1/synthesis", json=valid_request(return_timings=True))
    assert wav.status_code == 415
    assert wav.json()["error"]["code"] == "UNSUPPORTED_ENCODING"
    assert timings.status_code == 422
    assert timings.json()["error"]["code"] == "UNSUPPORTED_CAPABILITY"


def test_unknown_fields_controls_ranges_and_limits_are_rejected() -> None:
    cases = [
        (valid_request(extra=True), "INVALID_REQUEST"),
        (valid_request(controls={"nasality": 0.2}), "UNKNOWN_CONTROL"),
        (valid_request(controls={"pace": 2}), "CONTROL_OUT_OF_RANGE"),
        (valid_request(text="too long"), "LIMIT_EXCEEDED"),
    ]
    with client(request_limits=RequestLimits(max_text_characters=5)) as api:
        for payload, code in cases:
            response = api.post("/v1/synthesis", json=payload)
            assert response.status_code == 400
            assert response.json()["error"]["code"] == code


def test_errors_do_not_echo_synthesis_text() -> None:
    secret_text = "do-not-echo-private-speech"
    with client() as api:
        response = api.post("/v1/synthesis", json=valid_request(text=secret_text, extra=1))
    assert secret_text not in response.text


def test_cancel_is_idempotent_and_invalid_ids_are_rejected() -> None:
    with client() as api:
        first = api.delete("/v1/synthesis/unknown")
        second = api.delete("/v1/synthesis/unknown")
        invalid = api.delete("/v1/synthesis/..%2Fbad")
    assert first.status_code == 204
    assert second.status_code == 204
    assert invalid.status_code in {400, 404}


def test_malformed_json_has_stable_error_envelope() -> None:
    with client() as api:
        response = api.post(
            "/v1/synthesis",
            content=b"{bad",
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
