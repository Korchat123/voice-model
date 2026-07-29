"""Fail-closed dataset validation with auditable per-clip findings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from voice_model.data.audio import DEFAULT_AUDIO_POLICY, AudioPolicy, validate_wav
from voice_model.data.duplicates import duplicate_audio_groups, leakage_errors
from voice_model.data.hashes import sha256_file
from voice_model.data.manifest import DatasetManifest

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    message: str
    clip_id: str | None = None


def _safe_audio_path(dataset_root: Path, relative_path: str) -> Path | None:
    root = dataset_root.resolve()
    candidate = (root / relative_path).resolve()
    return candidate if candidate.is_relative_to(root) else None


def validate_manifest(
    manifest: DatasetManifest,
    dataset_root: Path,
    *,
    audio_policy: AudioPolicy = DEFAULT_AUDIO_POLICY,
) -> list[Finding]:
    findings: list[Finding] = []
    seen_ids: set[str] = set()
    for clip in manifest.clips:
        if clip.clip_id in seen_ids:
            findings.append(Finding("duplicate_clip_id", "clip_id must be unique", clip.clip_id))
        seen_ids.add(clip.clip_id)
        if clip.consent_status != "approved":
            findings.append(
                Finding("consent_not_approved", "clip consent must be approved", clip.clip_id)
            )
        if not clip.consent_id.strip():
            findings.append(Finding("missing_consent_id", "consent_id is required", clip.clip_id))
        if not clip.transcript.strip():
            findings.append(Finding("missing_transcript", "transcript is required", clip.clip_id))
        if not SHA256_PATTERN.fullmatch(clip.audio_sha256):
            findings.append(
                Finding("invalid_sha256", "audio_sha256 must be lowercase hex", clip.clip_id)
            )
            continue
        audio_path = _safe_audio_path(dataset_root, clip.audio_path)
        if audio_path is None:
            findings.append(Finding("unsafe_path", "audio_path escapes dataset root", clip.clip_id))
            continue
        if not audio_path.is_file():
            findings.append(
                Finding("missing_audio", f"audio file not found: {clip.audio_path}", clip.clip_id)
            )
            continue
        actual_hash = sha256_file(audio_path)
        if actual_hash != clip.audio_sha256:
            findings.append(
                Finding(
                    "hash_mismatch",
                    f"expected {clip.audio_sha256}, got {actual_hash}",
                    clip.clip_id,
                )
            )
        try:
            _, audio_errors = validate_wav(audio_path, audio_policy)
        except ValueError as exc:
            findings.append(Finding("invalid_audio", str(exc), clip.clip_id))
        else:
            findings.extend(
                Finding("audio_quality", message, clip.clip_id) for message in audio_errors
            )
    for group in duplicate_audio_groups(manifest.clips):
        findings.append(Finding("duplicate_audio", ", ".join(group)))
    findings.extend(Finding("split_leakage", message) for message in leakage_errors(manifest.clips))
    return findings
