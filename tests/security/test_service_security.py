from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from starlette.testclient import TestClient

from voice_model.domain import AudioEncoding, Language, RequestLimits, SynthesisRequest
from voice_model.engines.base import AudioChunk, CancellationToken, EngineCapabilities
from voice_model.engines.fake import FakeEngine
from voice_model.service import create_app
from voice_model.service.settings import ServiceSettings


def request(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "request_id": "security-1",
        "text": "safe generated test text",
        "language": "en",
        "voice": "primary",
    }
    value.update(updates)
    return value


def test_malformed_and_type_confused_inputs_fail_without_server_errors() -> None:
    cases: list[tuple[object, int]] = [
        ([], 400),
        (None, 400),
        ({"request_id": "missing-fields"}, 400),
        (request(text=123), 400),
        (request(seed=True), 400),
        (request(return_timings="yes"), 400),
        (request(controls=[]), 400),
        (request(unexpected={"deep": ["object"]}), 400),
    ]
    with TestClient(create_app(engine=FakeEngine())) as client:
        for payload, expected in cases:
            response = client.post("/v1/synthesis", json=payload)
            assert response.status_code == expected
            assert response.status_code < 500
            assert "traceback" not in response.text.casefold()

        non_finite = client.post(
            "/v1/synthesis",
            content=(
                b'{"request_id":"nan","text":"safe","language":"en",'
                b'"voice":"primary","controls":{"pitch":NaN}}'
            ),
            headers={"content-type": "application/json"},
        )
        assert non_finite.status_code == 400
        assert non_finite.status_code < 500


def test_utf8_byte_limit_is_enforced_before_synthesis() -> None:
    settings = ServiceSettings(
        request_limits=RequestLimits(
            max_text_characters=20,
            max_utf8_bytes=8,
            max_predicted_audio_ms=120_000,
        )
    )
    with TestClient(create_app(engine=FakeEngine(), settings=settings)) as client:
        response = client.post("/v1/synthesis", json=request(text="ก" * 4))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "LIMIT_EXCEEDED"


@pytest.mark.parametrize(
    "identifier",
    [
        "../private",
        "..%2Fprivate",
        r"C:\private\voice.wav",
        r"\\server\share\voice.wav",
        "file:///etc/passwd",
        "https://example.invalid/model",
        "name/with/slash",
    ],
)
def test_path_shaped_voice_identifiers_are_data_not_file_access(identifier: str) -> None:
    with TestClient(create_app(engine=FakeEngine())) as client:
        response = client.post("/v1/synthesis", json=request(voice=identifier))
    assert response.status_code in {400, 404}
    assert identifier not in response.text


def test_path_shaped_synthesis_text_is_not_interpreted_as_a_path() -> None:
    sentinel = r"C:\definitely-not-a-real-private-file.txt"
    with TestClient(
        create_app(engine=FakeEngine(chunk_frames=8, frames_per_character=1))
    ) as client:
        response = client.post("/v1/synthesis", json=request(text=sentinel))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/")
    assert sentinel.encode() not in response.content


def test_validation_response_and_logs_do_not_disclose_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sentinel = "SENSITIVE-SPEECH-7cb9850b"
    caplog.set_level(logging.DEBUG)
    with TestClient(create_app(engine=FakeEngine())) as client:
        response = client.post(
            "/v1/synthesis",
            json=request(text=sentinel, unexpected=True),
        )
    assert response.status_code == 400
    assert sentinel not in response.text
    assert sentinel not in caplog.text


class TextEchoingFailureEngine:
    @property
    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            model_id="failure-fixture",
            model_version="1",
            voices=frozenset({"primary"}),
            languages=frozenset({Language.ENGLISH}),
            encodings=frozenset({AudioEncoding.PCM_S16LE}),
            sample_rates_hz=frozenset({24_000}),
            controls=frozenset(),
        )

    def predict_duration_ms(self, request: SynthesisRequest) -> int:
        return 10

    def synthesize(
        self, request: SynthesisRequest, cancellation: CancellationToken
    ) -> Iterator[AudioChunk]:
        del cancellation
        raise RuntimeError(f"engine rejected private text: {request.text}")
        yield  # pragma: no cover


def test_engine_exception_logs_are_text_free(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sentinel = "SENSITIVE-ENGINE-FAILURE-5a33fc3e"
    caplog.set_level(logging.ERROR, logger="voice_model.service.routes")
    with TestClient(create_app(engine=TextEchoingFailureEngine())) as client:
        response = client.post("/v1/synthesis", json=request(text=sentinel))
    assert response.status_code == 200
    assert sentinel not in response.content.decode(errors="ignore")
    assert sentinel not in caplog.text
