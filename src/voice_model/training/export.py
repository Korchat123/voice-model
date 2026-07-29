"""Versioned export manifest creation and verification."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from voice_model.data.hashes import sha256_file
from voice_model.training.metadata import write_canonical_json


def export_fixture_model(
    *,
    run_dir: Path,
    export_dir: Path,
    model_id: str,
    model_version: str,
) -> Path:
    metadata_path = run_dir / "run-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or metadata.get("fixture_only") is not True:
        raise ValueError("only fixture-only run metadata can be exported")
    approvals = metadata.get("approvals")
    if not isinstance(approvals, dict) or any(
        approvals.get(key) is not True for key in ("consent", "license", "data")
    ):
        raise ValueError("all approvals must be true before export")
    selected = metadata.get("selected_checkpoint")
    if not isinstance(selected, dict):
        raise ValueError("selected checkpoint metadata is required")
    relative = selected.get("artifact_path")
    expected_hash = selected.get("artifact_sha256")
    if not isinstance(relative, str) or not isinstance(expected_hash, str):
        raise ValueError("selected checkpoint path and hash are required")
    checkpoint = (run_dir.resolve() / relative).resolve()
    if not checkpoint.is_relative_to(run_dir.resolve()):
        raise ValueError("checkpoint path escapes run directory")
    if sha256_file(checkpoint) != expected_hash:
        raise ValueError("selected checkpoint hash mismatch")
    if export_dir.exists():
        raise FileExistsError(f"export directory already exists: {export_dir}")
    export_dir.mkdir(parents=True)
    target = export_dir / "model.fixture.json"
    shutil.copyfile(checkpoint, target)
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "fixture_only": True,
        "model_id": model_id,
        "model_version": model_version,
        "model_file": target.name,
        "model_sha256": sha256_file(target),
        "run_metadata_sha256": sha256_file(metadata_path),
        "engine": metadata["engine"],
        "dataset": metadata["dataset"],
        "code_revision": metadata["code_revision"],
        "config_sha256": metadata["config_sha256"],
    }
    manifest_path = export_dir / "export-manifest.json"
    manifest["manifest_payload_sha256"] = write_canonical_json(
        export_dir / "manifest-payload.json", manifest
    )
    write_canonical_json(manifest_path, manifest)
    return manifest_path


def verify_export(export_dir: Path) -> bool:
    manifest_path = export_dir / "export-manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("fixture_only") is not True:
        return False
    model_file = data.get("model_file")
    model_hash = data.get("model_sha256")
    if not isinstance(model_file, str) or not isinstance(model_hash, str):
        return False
    model_path = (export_dir.resolve() / model_file).resolve()
    return model_path.is_relative_to(export_dir.resolve()) and sha256_file(model_path) == model_hash
