"""Bounded request admission and shared cancellation lifecycle."""

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from enum import StrEnum

from voice_model.engines import CancellationToken


class CapacityExceededError(RuntimeError):
    pass


class RequestConflictError(RuntimeError):
    pass


class RequestState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(slots=True)
class RequestEntry:
    token: CancellationToken
    state: RequestState


class RequestLifecycle:
    """Own request uniqueness, bounded queueing, and terminal tombstones."""

    def __init__(self, max_active: int, max_queued: int, tombstone_limit: int) -> None:
        self._max_active = max_active
        self._max_queued = max_queued
        self._tombstone_limit = tombstone_limit
        self._active = 0
        self._entries: OrderedDict[str, RequestEntry] = OrderedDict()
        self._condition = asyncio.Condition()

    async def admit(self, request_id: str) -> CancellationToken:
        async with self._condition:
            if request_id in self._entries:
                raise RequestConflictError
            pending = sum(
                entry.state in {RequestState.QUEUED, RequestState.RUNNING}
                for entry in self._entries.values()
            )
            if pending >= self._max_active + self._max_queued:
                raise CapacityExceededError
            token = CancellationToken()
            self._entries[request_id] = RequestEntry(token, RequestState.QUEUED)
            return token

    async def activate(self, request_id: str) -> bool:
        async with self._condition:
            entry = self._entries[request_id]
            await self._condition.wait_for(
                lambda: self._active < self._max_active or entry.token.is_cancelled
            )
            if entry.token.is_cancelled:
                entry.state = RequestState.CANCELLED
                return False
            self._active += 1
            entry.state = RequestState.RUNNING
            return True

    async def finish(self, request_id: str, state: RequestState) -> None:
        async with self._condition:
            entry = self._entries[request_id]
            if entry.state is RequestState.RUNNING:
                self._active -= 1
            entry.state = RequestState.CANCELLED if entry.token.is_cancelled else state
            self._entries.move_to_end(request_id)
            self._prune()
            self._condition.notify_all()

    async def cancel(self, request_id: str) -> bool:
        async with self._condition:
            entry = self._entries.get(request_id)
            if entry is None or entry.state not in {RequestState.QUEUED, RequestState.RUNNING}:
                return False
            entry.token.cancel()
            self._condition.notify_all()
            return True

    def _prune(self) -> None:
        terminal = {
            RequestState.COMPLETED,
            RequestState.CANCELLED,
            RequestState.FAILED,
        }
        while len(self._entries) > self._tombstone_limit:
            key, entry = next(iter(self._entries.items()))
            if entry.state not in terminal:
                break
            del self._entries[key]
