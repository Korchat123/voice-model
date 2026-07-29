"""Explicit placeholder used for approval-gated candidate configurations."""

from collections.abc import Mapping

from voice_model.engines.base import Engine


def create_approval_gated_adapter(
    settings: Mapping[str, str | int | float | bool | None],
) -> Engine:
    del settings
    raise PermissionError("real engine adapter is approval-gated and not implemented")
