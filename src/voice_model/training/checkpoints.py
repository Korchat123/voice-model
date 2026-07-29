"""Checkpoint metadata and deterministic selection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Checkpoint:
    step: int
    validation_score: float
    artifact_path: str
    artifact_sha256: str

    def to_dict(self) -> dict[str, int | float | str]:
        return {
            "step": self.step,
            "validation_score": self.validation_score,
            "artifact_path": self.artifact_path,
            "artifact_sha256": self.artifact_sha256,
        }


def select_checkpoint(checkpoints: tuple[Checkpoint, ...]) -> Checkpoint:
    """Select highest score, then earliest step, then digest."""
    if not checkpoints:
        raise ValueError("at least one checkpoint is required")
    return sorted(
        checkpoints,
        key=lambda checkpoint: (
            -checkpoint.validation_score,
            checkpoint.step,
            checkpoint.artifact_sha256,
        ),
    )[0]
