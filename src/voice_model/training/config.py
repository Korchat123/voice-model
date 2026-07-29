"""Strict training configuration with fail-closed approval gates."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from voice_model.data.hashes import sha256_file

SCHEMA_VERSION = 1


def _table(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"[{key}] table is required")
    return value


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _approved(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if value is not True:
        raise ValueError(f"{key} must be explicitly true")
    return True


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    config_sha256: str
    seed: int
    trainer: str
    max_steps: int
    dataset_manifest: str
    dataset_sha256: str
    consent_approved: bool
    license_approved: bool
    data_approved: bool
    engine_id: str
    engine_version: str
    engine_sha256: str


def load_training_config(path: Path) -> TrainingConfig:
    """Load a pinned config, refusing placeholders and incomplete approvals."""
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    run = _table(data, "run")
    dataset = _table(data, "dataset")
    approvals = _table(data, "approvals")
    engine = _table(data, "engine")
    trainer = _text(run, "trainer")
    if trainer != "deterministic-fixture-v1":
        raise ValueError("only deterministic-fixture-v1 is supported by this infrastructure")
    seed = run.get("seed")
    max_steps = run.get("max_steps")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    if (
        not isinstance(max_steps, int)
        or isinstance(max_steps, bool)
        or not 1 <= max_steps <= 10_000
    ):
        raise ValueError("max_steps must be an integer in [1, 10000]")
    dataset_sha256 = _text(dataset, "manifest_sha256").lower()
    engine_sha256 = _text(engine, "sha256").lower()
    for field, digest in {
        "dataset.manifest_sha256": dataset_sha256,
        "engine.sha256": engine_sha256,
    }.items():
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"{field} must be lowercase SHA-256 hex")
    values = (
        _text(engine, "id"),
        _text(engine, "version"),
        _text(dataset, "manifest"),
    )
    if any(
        "USER_INPUT_REQUIRED" in value or value.lower() in {"latest", "main"} for value in values
    ):
        raise ValueError("engine and dataset references must be immutable and fully resolved")
    return TrainingConfig(
        config_sha256=sha256_file(path),
        seed=seed,
        trainer=trainer,
        max_steps=max_steps,
        dataset_manifest=values[2],
        dataset_sha256=dataset_sha256,
        consent_approved=_approved(approvals, "consent"),
        license_approved=_approved(approvals, "license"),
        data_approved=_approved(approvals, "data"),
        engine_id=values[0],
        engine_version=values[1],
        engine_sha256=engine_sha256,
    )
