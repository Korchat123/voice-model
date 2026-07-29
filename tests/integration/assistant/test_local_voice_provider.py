"""Reference assistant-provider integration tests."""

import asyncio
import importlib.util
import json
import sys
from collections.abc import Coroutine
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

import httpx
import pytest


def load_provider() -> ModuleType:
    path = Path(__file__).parents[3] / "examples" / "assistant-client" / "local_voice_provider.py"
    spec = importlib.util.spec_from_file_location("local_voice_provider", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


provider_module = load_provider()


T = TypeVar("T")


def run(coroutine: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coroutine)


def test_sanitizer_normalizes_and_rejects_non_speech_content() -> None:
    sanitize = provider_module.sanitize_speech_text
    assert sanitize("  hello\n  world  ") == "hello world"
    for unsafe in ("https://example.test", "```python", "api_key = private", "\x00"):
        with pytest.raises(provider_module.UnsafeSpeechTextError):
            sanitize(unsafe)


def test_controls_enforce_public_bounds() -> None:
    assert provider_module.VoiceControls(resonance=0.2).as_request() == {"resonance": 0.2}
    with pytest.raises(ValueError):
        provider_module.VoiceControls(pace=1.1).as_request()


def test_stream_uses_sanitized_text_controls_and_same_request_id() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            headers={"X-Request-ID": "turn-42"},
            content=b"\x01\x00\x02\x00",
        )

    async def scenario() -> bytes:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://voice.test"
        )
        voice = provider_module.LocalVoiceProvider(client=client)
        chunks = [
            chunk
            async for chunk in voice.stream(
                "  hello\nworld ",
                request_id="turn-42",
                preset="warm",
                controls=provider_module.VoiceControls(resonance=0.2),
            )
        ]
        await client.aclose()
        assert voice.last_diagnostic.status == "completed"
        return b"".join(chunks)

    assert run(scenario()) == b"\x01\x00\x02\x00"
    payload = json.loads(seen[0].content)
    assert payload["text"] == "hello world"
    assert payload["request_id"] == "turn-42"
    assert payload["controls"] == {"resonance": 0.2}
    assert seen[0].headers["x-request-id"] == "turn-42"


def test_barge_in_uses_active_request_id_and_is_idempotent() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(204)

    async def scenario() -> tuple[bool, bool]:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://voice.test"
        )
        voice = provider_module.LocalVoiceProvider(client=client)
        first = await voice.barge_in("turn-9")
        second = await voice.barge_in("turn-9")
        await client.aclose()
        return first, second

    assert run(scenario()) == (True, True)
    assert paths == ["/v1/synthesis/turn-9", "/v1/synthesis/turn-9"]


def test_player_can_barge_in_without_tracking_a_second_request_id() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.method == "POST":
            return httpx.Response(200, headers={"X-Request-ID": "turn-active"}, content=b"\x00\x00")
        return httpx.Response(202)

    async def scenario() -> bool:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://voice.test"
        )
        voice = provider_module.LocalVoiceProvider(client=client)

        async def play(_chunk: bytes) -> None:
            assert await voice.barge_in()

        succeeded = await voice.stream_to_player("hello", play, request_id="turn-active")
        await client.aclose()
        return bool(succeeded)

    assert run(scenario())
    assert paths == ["/v1/synthesis", "/v1/synthesis/turn-active"]


def test_voice_failure_does_not_escape_player_boundary_or_log_text() -> None:
    private_text = "private spoken sentence"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    async def scenario() -> tuple[bool, Any]:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://voice.test"
        )
        voice = provider_module.LocalVoiceProvider(client=client)

        async def play(_chunk: bytes) -> None:
            raise AssertionError("no audio should be played")

        succeeded = await voice.stream_to_player(private_text, play, request_id="turn-failure")
        diagnostic = voice.last_diagnostic
        await client.aclose()
        return succeeded, diagnostic

    succeeded, diagnostic = run(scenario())
    assert not succeeded
    assert diagnostic.request_id == "turn-failure"
    assert private_text not in repr(diagnostic)


def test_capability_failure_is_recoverable_and_privacy_safe() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async def scenario() -> None:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://voice.test"
        )
        voice = provider_module.LocalVoiceProvider(client=client)
        with pytest.raises(provider_module.VoiceServiceError):
            await voice.capabilities()
        await client.aclose()

    run(scenario())
