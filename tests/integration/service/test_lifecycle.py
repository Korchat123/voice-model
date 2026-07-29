"""Request lifecycle, queue, cancellation, and tombstone tests."""

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

import pytest

from voice_model.service.lifecycle import (
    CapacityExceededError,
    RequestConflictError,
    RequestLifecycle,
    RequestState,
)

T = TypeVar("T")


def run(coroutine: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coroutine)


def test_capacity_is_bounded_before_model_work() -> None:
    async def scenario() -> None:
        lifecycle = RequestLifecycle(max_active=1, max_queued=1, tombstone_limit=4)
        await lifecycle.admit("one")
        await lifecycle.admit("two")
        with pytest.raises(CapacityExceededError):
            await lifecycle.admit("three")

    run(scenario())


def test_duplicate_active_and_tombstoned_ids_conflict() -> None:
    async def scenario() -> None:
        lifecycle = RequestLifecycle(max_active=1, max_queued=0, tombstone_limit=4)
        await lifecycle.admit("one")
        with pytest.raises(RequestConflictError):
            await lifecycle.admit("one")
        assert await lifecycle.activate("one")
        await lifecycle.finish("one", RequestState.COMPLETED)
        with pytest.raises(RequestConflictError):
            await lifecycle.admit("one")

    run(scenario())


def test_queued_cancellation_unblocks_without_activation() -> None:
    async def scenario() -> None:
        lifecycle = RequestLifecycle(max_active=1, max_queued=1, tombstone_limit=4)
        await lifecycle.admit("running")
        assert await lifecycle.activate("running")
        token = await lifecycle.admit("queued")
        activation = asyncio.create_task(lifecycle.activate("queued"))
        assert await lifecycle.cancel("queued")
        assert not await activation
        assert token.is_cancelled
        await lifecycle.finish("queued", RequestState.CANCELLED)
        await lifecycle.finish("running", RequestState.COMPLETED)
        assert not await lifecycle.cancel("queued")

    run(scenario())


def test_finishing_active_request_allows_next_queued_request() -> None:
    async def scenario() -> None:
        lifecycle = RequestLifecycle(max_active=1, max_queued=1, tombstone_limit=4)
        await lifecycle.admit("one")
        assert await lifecycle.activate("one")
        await lifecycle.admit("two")
        activation = asyncio.create_task(lifecycle.activate("two"))
        await lifecycle.finish("one", RequestState.COMPLETED)
        assert await activation
        await lifecycle.finish("two", RequestState.COMPLETED)

    run(scenario())
