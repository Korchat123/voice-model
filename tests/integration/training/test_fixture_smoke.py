from __future__ import annotations

import json
from pathlib import Path

import pytest

from voice_model.data.hashes import sha256_file
from voice_model.training.config import load_training_config
from voice_model.training.export import export_fixture_model, verify_export
from voice_model.training.run import run_fixture_training


@pytest.mark.training_smoke
def test_fixture_training_to_export(tmp_path: Path) -> None:
    engine_digest = "2" * 64
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "dataset_id": "smoke-fixture",
                "dataset_version": "1",
                "clips": [
                    {
                        "clip_id": "fixture-1",
                        "audio_path": "unused.wav",
                        "audio_sha256": "1" * 64,
                        "transcript": "No real voice is trained.",
                        "language": "en",
                        "speaker_id": "synthetic-test-signal",
                        "consent_id": "generated-fixture",
                        "consent_status": "approved",
                        "source_license": "CC0-1.0",
                        "prompt_family_id": "fixture",
                        "split": "train",
                        "style": "neutral",
                        "processing_lineage": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    config = tmp_path / "training.toml"
    config.write_text(
        f"""
schema_version = 1
[run]
trainer = "deterministic-fixture-v1"
seed = 7
max_steps = 2
[dataset]
manifest = "manifest.json"
manifest_sha256 = "{sha256_file(manifest)}"
[approvals]
consent = true
license = true
data = true
[engine]
id = "fixture-engine"
version = "1.0.0"
sha256 = "{engine_digest}"
""",
        encoding="utf-8",
    )
    result = run_fixture_training(
        load_training_config(config),
        dataset_root=tmp_path,
        output_dir=tmp_path / "run",
        code_revision="smoke-revision",
    )
    assert result.selected_checkpoint.artifact_sha256
    export_fixture_model(
        run_dir=tmp_path / "run",
        export_dir=tmp_path / "export",
        model_id="fixture-model",
        model_version="1",
    )
    assert verify_export(tmp_path / "export")
