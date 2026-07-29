"""Deterministic fixture trainer used to validate infrastructure only."""

from __future__ import annotations

import hashlib
import platform
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from voice_model.data.hashes import sha256_file
from voice_model.data.manifest import load_manifest
from voice_model.training.checkpoints import Checkpoint, select_checkpoint
from voice_model.training.config import TrainingConfig
from voice_model.training.metadata import write_canonical_json


@dataclass(frozen=True, slots=True)
class TrainingResult:
    run_metadata_path: Path
    run_metadata_sha256: str
    selected_checkpoint: Checkpoint


def _resolve_under(root: Path, relative: str) -> Path:
    resolved_root = root.resolve()
    candidate = (resolved_root / relative).resolve()
    if not candidate.is_relative_to(resolved_root):
        raise ValueError("dataset manifest path escapes dataset root")
    return candidate


def run_fixture_training(
    config: TrainingConfig,
    *,
    dataset_root: Path,
    output_dir: Path,
    code_revision: str,
) -> TrainingResult:
    """Create deterministic fake checkpoints and complete reproducibility metadata."""
    if not code_revision.strip() or code_revision.lower() in {"unknown", "dirty"}:
        raise ValueError("an immutable code revision is required")
    manifest_path = _resolve_under(dataset_root, config.dataset_manifest)
    if sha256_file(manifest_path) != config.dataset_sha256:
        raise ValueError("dataset manifest hash does not match pinned configuration")
    manifest = load_manifest(manifest_path)
    if not manifest.clips:
        raise ValueError("dataset manifest must contain clips")
    if any(clip.consent_status != "approved" for clip in manifest.clips):
        raise ValueError("every training clip must have approved consent")
    if any(not clip.source_license.strip() for clip in manifest.clips):
        raise ValueError("every training clip must have a source license")
    if any(clip.split is None for clip in manifest.clips):
        raise ValueError("every training clip must have an assigned split")

    output_dir.mkdir(parents=True, exist_ok=False)
    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_dir.mkdir()
    generator = random.Random(config.seed)
    checkpoints: list[Checkpoint] = []
    for step in range(1, config.max_steps + 1):
        payload: dict[str, Any] = {
            "fixture_only": True,
            "trainer": config.trainer,
            "seed": config.seed,
            "step": step,
            "weights": [generator.randrange(-10_000, 10_001) for _ in range(8)],
        }
        artifact = checkpoint_dir / f"step-{step:06d}.fixture.json"
        digest = write_canonical_json(artifact, payload)
        score_seed = hashlib.sha256(f"{digest}\0validation".encode()).digest()
        score = int.from_bytes(score_seed[:8], "big") / (1 << 64)
        checkpoints.append(
            Checkpoint(
                step=step,
                validation_score=score,
                artifact_path=artifact.relative_to(output_dir).as_posix(),
                artifact_sha256=digest,
            )
        )
    selected = select_checkpoint(tuple(checkpoints))
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "fixture_only": True,
        "code_revision": code_revision,
        "config_sha256": config.config_sha256,
        "dataset": {
            "id": manifest.dataset_id,
            "version": manifest.dataset_version,
            "manifest_sha256": config.dataset_sha256,
        },
        "engine": {
            "id": config.engine_id,
            "version": config.engine_version,
            "sha256": config.engine_sha256,
        },
        "approvals": {
            "consent": config.consent_approved,
            "license": config.license_approved,
            "data": config.data_approved,
        },
        "seed": config.seed,
        "trainer": config.trainer,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "executable_name": Path(sys.executable).name,
        "checkpoints": [checkpoint.to_dict() for checkpoint in checkpoints],
        "selected_checkpoint": selected.to_dict(),
    }
    metadata_path = output_dir / "run-metadata.json"
    metadata_sha256 = write_canonical_json(metadata_path, metadata)
    return TrainingResult(metadata_path, metadata_sha256, selected)
