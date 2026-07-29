"""Deterministic prompt-family-aware dataset splitting."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from voice_model.data.manifest import ClipRecord, DatasetManifest, Split


def _family_split(
    dataset_id: str,
    family_id: str,
    *,
    seed: str,
    train_ratio: float,
    validation_ratio: float,
) -> Split:
    digest = hashlib.sha256(f"{seed}\0{dataset_id}\0{family_id}".encode()).digest()
    point = int.from_bytes(digest[:8], "big") / (1 << 64)
    if point < train_ratio:
        return "train"
    if point < train_ratio + validation_ratio:
        return "validation"
    return "held_out"


def assign_splits(
    manifest: DatasetManifest,
    *,
    seed: str,
    train_ratio: float = 0.8,
    validation_ratio: float = 0.1,
) -> DatasetManifest:
    if not seed:
        raise ValueError("seed must be non-empty")
    if train_ratio <= 0 or validation_ratio <= 0:
        raise ValueError("train and validation ratios must be positive")
    if train_ratio + validation_ratio >= 1:
        raise ValueError("train_ratio + validation_ratio must be below 1")
    families: dict[str, list[ClipRecord]] = defaultdict(list)
    for clip in manifest.clips:
        families[clip.prompt_family_id].append(clip)
    assigned: dict[str, Split] = {
        family_id: _family_split(
            manifest.dataset_id,
            family_id,
            seed=seed,
            train_ratio=train_ratio,
            validation_ratio=validation_ratio,
        )
        for family_id in families
    }
    return DatasetManifest(
        dataset_id=manifest.dataset_id,
        dataset_version=manifest.dataset_version,
        schema_version=manifest.schema_version,
        clips=tuple(clip.with_split(assigned[clip.prompt_family_id]) for clip in manifest.clips),
    )
