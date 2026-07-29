from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from voice_model.data.hashes import sha256_file
from voice_model.training.checkpoints import Checkpoint, select_checkpoint
from voice_model.training.config import load_training_config
from voice_model.training.export import export_fixture_model, verify_export
from voice_model.training.run import run_fixture_training


def write_manifest(path: Path, *, consent: str = "approved") -> None:
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "dataset_id": "fixture",
        "dataset_version": "1.0.0",
        "clips": [
            {
                "clip_id": "generated-1",
                "audio_path": "unused.wav",
                "audio_sha256": "1" * 64,
                "transcript": "Generated fixture metadata",
                "language": "en",
                "speaker_id": "synthetic-test-signal",
                "consent_id": "generated-fixture",
                "consent_status": consent,
                "source_license": "CC0-1.0",
                "prompt_family_id": "fixture-1",
                "split": "train",
                "style": "neutral",
                "processing_lineage": [],
            }
        ],
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def write_config(
    path: Path,
    manifest_hash: str,
    *,
    consent: bool = True,
    engine_hash: str = "2" * 64,
) -> None:
    path.write_text(
        f"""
schema_version = 1
[run]
trainer = "deterministic-fixture-v1"
seed = 42
max_steps = 3
[dataset]
manifest = "manifest.json"
manifest_sha256 = "{manifest_hash}"
[approvals]
consent = {str(consent).lower()}
license = true
data = true
[engine]
id = "fixture-engine"
version = "1.0.0"
sha256 = "{engine_hash}"
""".strip()
        + "\n",
        encoding="utf-8",
    )


def prepared_config(tmp_path: Path) -> Path:
    manifest = tmp_path / "manifest.json"
    config = tmp_path / "training.toml"
    write_manifest(manifest)
    write_config(config, sha256_file(manifest))
    return config


def test_config_fails_closed_for_unapproved_consent(tmp_path: Path) -> None:
    config = prepared_config(tmp_path)
    write_config(config, sha256_file(tmp_path / "manifest.json"), consent=False)
    with pytest.raises(ValueError, match="consent must be explicitly true"):
        load_training_config(config)


def test_config_rejects_unpinned_engine(tmp_path: Path) -> None:
    config = prepared_config(tmp_path)
    write_config(config, sha256_file(tmp_path / "manifest.json"), engine_hash="latest")
    with pytest.raises(ValueError, match="SHA-256"):
        load_training_config(config)


def test_checkpoint_selection_is_deterministic() -> None:
    checkpoints = (
        Checkpoint(3, 0.8, "three", "3" * 64),
        Checkpoint(2, 0.8, "two", "2" * 64),
        Checkpoint(1, 0.5, "one", "1" * 64),
    )
    assert select_checkpoint(checkpoints).step == 2
    with pytest.raises(ValueError, match="at least one"):
        select_checkpoint(())


def test_fixture_training_is_reproducible(tmp_path: Path) -> None:
    config_path = prepared_config(tmp_path)
    config = load_training_config(config_path)
    first = run_fixture_training(
        config,
        dataset_root=tmp_path,
        output_dir=tmp_path / "run-1",
        code_revision="abc123",
    )
    second = run_fixture_training(
        config,
        dataset_root=tmp_path,
        output_dir=tmp_path / "run-2",
        code_revision="abc123",
    )
    assert first.run_metadata_sha256 == second.run_metadata_sha256
    assert first.selected_checkpoint == second.selected_checkpoint


def test_training_rejects_changed_manifest(tmp_path: Path) -> None:
    config = load_training_config(prepared_config(tmp_path))
    (tmp_path / "manifest.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        run_fixture_training(
            config,
            dataset_root=tmp_path,
            output_dir=tmp_path / "run",
            code_revision="abc123",
        )


def test_export_is_checksummed_and_detects_tampering(tmp_path: Path) -> None:
    config = load_training_config(prepared_config(tmp_path))
    run_fixture_training(
        config,
        dataset_root=tmp_path,
        output_dir=tmp_path / "run",
        code_revision="abc123",
    )
    export_fixture_model(
        run_dir=tmp_path / "run",
        export_dir=tmp_path / "export",
        model_id="fixture-model",
        model_version="1.0.0",
    )
    assert verify_export(tmp_path / "export")
    (tmp_path / "export/model.fixture.json").write_text("tampered", encoding="utf-8")
    assert not verify_export(tmp_path / "export")
