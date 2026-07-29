from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path
from typing import Any

import pytest

from voice_model.data.audio import AudioPolicy, validate_wav
from voice_model.data.hashes import sha256_file
from voice_model.data.manifest import DatasetManifest, load_manifest
from voice_model.data.splits import assign_splits
from voice_model.data.validation import validate_manifest


def write_tone(path: Path, *, clipped: bool = False) -> None:
    rate = 24_000
    frames = bytearray()
    for index in range(rate // 2):
        value = 32_767 if clipped else int(2_000 * math.sin(2 * math.pi * 220 * index / rate))
        frames.extend(struct.pack("<h", value))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(frames)


def clip_dict(path: str, digest: str, *, clip_id: str = "clip-1") -> dict[str, Any]:
    return {
        "clip_id": clip_id,
        "audio_path": path,
        "audio_sha256": digest,
        "transcript": "ทดสอบ a generated tone",
        "language": "mixed",
        "speaker_id": "synthetic-test-signal",
        "consent_id": "generated-fixture",
        "consent_status": "approved",
        "source_license": "CC0-1.0",
        "prompt_family_id": f"family-{clip_id}",
        "split": None,
        "style": "neutral",
        "processing_lineage": [],
    }


def manifest_for(*clips: dict[str, Any]) -> DatasetManifest:
    return DatasetManifest.from_dict(
        {
            "schema_version": "1.0",
            "dataset_id": "fixture",
            "dataset_version": "1.0.0",
            "clips": list(clips),
        }
    )


def test_manifest_round_trip_and_safe_paths(tmp_path: Path) -> None:
    source = Path("tests/fixtures/dataset/manifest.example.json")
    manifest = load_manifest(source)
    assert DatasetManifest.from_dict(manifest.to_dict()) == manifest
    invalid = manifest.to_dict()
    invalid["clips"][0]["audio_path"] = "../private.wav"
    with pytest.raises(ValueError, match="safe relative POSIX"):
        DatasetManifest.from_dict(invalid)


def test_audio_validation_detects_clipping(tmp_path: Path) -> None:
    clean = tmp_path / "clean.wav"
    clipped = tmp_path / "clipped.wav"
    write_tone(clean)
    write_tone(clipped, clipped=True)
    _, clean_errors = validate_wav(clean)
    metrics, clipped_errors = validate_wav(clipped)
    assert clean_errors == []
    assert metrics.clipped_fraction == 1.0
    assert any("clipped_fraction" in error for error in clipped_errors)


def test_validation_checks_hash_consent_duplicates_and_leakage(tmp_path: Path) -> None:
    audio = tmp_path / "tone.wav"
    write_tone(audio)
    digest = sha256_file(audio)
    first = clip_dict("tone.wav", digest)
    first["split"] = "train"
    second = clip_dict("tone.wav", digest, clip_id="clip-2")
    second["split"] = "held_out"
    second["prompt_family_id"] = first["prompt_family_id"]
    second["consent_status"] = "revoked"
    findings = validate_manifest(manifest_for(first, second), tmp_path)
    codes = {finding.code for finding in findings}
    assert {"consent_not_approved", "duplicate_audio", "split_leakage"} <= codes


def test_validation_rejects_hash_mismatch_and_audio_policy(tmp_path: Path) -> None:
    audio = tmp_path / "tone.wav"
    write_tone(audio)
    manifest = manifest_for(clip_dict("tone.wav", "0" * 64))
    findings = validate_manifest(
        manifest,
        tmp_path,
        audio_policy=AudioPolicy(sample_rate_hz=16_000),
    )
    assert {finding.code for finding in findings} == {"hash_mismatch", "audio_quality"}


def test_split_is_deterministic_and_keeps_families_together() -> None:
    clips = []
    for index in range(40):
        item = clip_dict(f"{index}.wav", f"{index:064x}", clip_id=f"clip-{index}")
        item["prompt_family_id"] = f"family-{index // 2}"
        clips.append(item)
    manifest = manifest_for(*clips)
    first = assign_splits(manifest, seed="fixed-seed")
    second = assign_splits(manifest, seed="fixed-seed")
    assert first == second
    family_splits: dict[str, set[str | None]] = {}
    for clip in first.clips:
        family_splits.setdefault(clip.prompt_family_id, set()).add(clip.split)
    assert all(len(splits) == 1 for splits in family_splits.values())
    assert {clip.split for clip in first.clips} == {"train", "validation", "held_out"}


def test_manifest_requires_supported_version() -> None:
    with pytest.raises(ValueError, match="unsupported schema_version"):
        DatasetManifest.from_dict(
            {
                "schema_version": "2.0",
                "dataset_id": "fixture",
                "dataset_version": "1",
                "clips": [],
            }
        )


def test_fixture_is_metadata_only() -> None:
    fixture = json.loads(
        Path("tests/fixtures/dataset/manifest.example.json").read_text(encoding="utf-8")
    )
    assert fixture["clips"][0]["speaker_id"] == "synthetic-test-signal"
