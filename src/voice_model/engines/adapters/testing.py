"""Factories available only for tests and local contract development."""

from collections.abc import Mapping

from voice_model.engines.base import Engine
from voice_model.engines.fake import FakeEngine


def create_deterministic_test_adapter(
    settings: Mapping[str, str | int | float | bool | None],
) -> Engine:
    chunk_samples = settings.get("chunk_samples", 240)
    if isinstance(chunk_samples, bool) or not isinstance(chunk_samples, int):
        raise ValueError("chunk_samples must be an integer")
    return FakeEngine(chunk_frames=chunk_samples)
