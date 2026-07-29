from __future__ import annotations

import asyncio

import pytest
from starlette.testclient import TestClient

from voice_model.engines.fake import FakeEngine
from voice_model.service import create_app
from voice_model.service.lifecycle import (
    CapacityExceededError,
    RequestLifecycle,
    RequestState,
)
from voice_model.service.settings import ServiceSettings


@pytest.mark.load
def test_repeated_requests_have_bounded_deterministic_output() -> None:
    settings = ServiceSettings(max_concurrent_requests=1, max_queued_requests=1)
    app = create_app(
        engine=FakeEngine(chunk_frames=16, frames_per_character=2),
        settings=settings,
    )
    payload = {
        "request_id": "load-0",
        "text": "bounded",
        "language": "en",
        "voice": "primary",
    }
    sizes: list[int] = []
    with TestClient(app) as client:
        for index in range(100):
            payload["request_id"] = f"load-{index}"
            response = client.post("/v1/synthesis", json=payload)
            assert response.status_code == 200
            sizes.append(len(response.content))
    assert set(sizes) == {len("bounded") * 2 * 2}


@pytest.mark.load
def test_lifecycle_rejects_excess_capacity_and_recovers() -> None:
    async def exercise() -> None:
        lifecycle = RequestLifecycle(max_active=1, max_queued=1, tombstone_limit=8)
        await lifecycle.admit("active")
        assert await lifecycle.activate("active")
        await lifecycle.admit("queued")
        with pytest.raises(CapacityExceededError):
            await lifecycle.admit("rejected")

        queued_activation = asyncio.create_task(lifecycle.activate("queued"))
        await asyncio.sleep(0)
        assert not queued_activation.done()
        await lifecycle.finish("active", RequestState.COMPLETED)
        assert await asyncio.wait_for(queued_activation, timeout=0.5)
        await lifecycle.finish("queued", RequestState.COMPLETED)

        await lifecycle.admit("recovered")
        assert await lifecycle.activate("recovered")
        await lifecycle.finish("recovered", RequestState.COMPLETED)

    asyncio.run(exercise())
