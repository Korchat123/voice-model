"""Versioned dataset manifest domain models."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

SCHEMA_VERSION = "1.0"
Language = Literal["th", "en", "mixed"]
Split = Literal["train", "validation", "held_out"]
ConsentStatus = Literal["approved", "revoked"]


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class ProcessingStep:
    """One reproducible processing operation."""

    operation: str
    tool: str
    tool_version: str
    config_sha256: str
    input_sha256: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProcessingStep:
        return cls(
            operation=_required_string(data, "operation"),
            tool=_required_string(data, "tool"),
            tool_version=_required_string(data, "tool_version"),
            config_sha256=_required_string(data, "config_sha256"),
            input_sha256=_required_string(data, "input_sha256"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "operation": self.operation,
            "tool": self.tool,
            "tool_version": self.tool_version,
            "config_sha256": self.config_sha256,
            "input_sha256": self.input_sha256,
        }


@dataclass(frozen=True, slots=True)
class ClipRecord:
    """Immutable metadata for one dataset utterance."""

    clip_id: str
    audio_path: str
    audio_sha256: str
    transcript: str
    language: Language
    speaker_id: str
    consent_id: str
    consent_status: ConsentStatus
    source_license: str
    prompt_family_id: str
    split: Split | None = None
    style: str = "neutral"
    processing_lineage: tuple[ProcessingStep, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClipRecord:
        language = _required_string(data, "language")
        if language not in {"th", "en", "mixed"}:
            raise ValueError(f"unsupported language: {language}")
        consent_status = _required_string(data, "consent_status")
        if consent_status not in {"approved", "revoked"}:
            raise ValueError(f"unsupported consent_status: {consent_status}")
        raw_split = data.get("split")
        if raw_split is not None and raw_split not in {"train", "validation", "held_out"}:
            raise ValueError(f"unsupported split: {raw_split}")
        raw_lineage = data.get("processing_lineage", [])
        if not isinstance(raw_lineage, list):
            raise ValueError("processing_lineage must be an array")
        if not all(isinstance(item, dict) for item in raw_lineage):
            raise ValueError("every processing_lineage entry must be an object")
        path = _required_string(data, "audio_path")
        pure_path = PurePosixPath(path)
        if pure_path.is_absolute() or ".." in pure_path.parts or "\\" in path:
            raise ValueError("audio_path must be a safe relative POSIX path")
        return cls(
            clip_id=_required_string(data, "clip_id"),
            audio_path=path,
            audio_sha256=_required_string(data, "audio_sha256").lower(),
            transcript=_required_string(data, "transcript"),
            language=cast(Language, language),
            speaker_id=_required_string(data, "speaker_id"),
            consent_id=_required_string(data, "consent_id"),
            consent_status=cast(ConsentStatus, consent_status),
            source_license=_required_string(data, "source_license"),
            prompt_family_id=_required_string(data, "prompt_family_id"),
            split=cast(Split | None, raw_split),
            style=str(data.get("style", "neutral")),
            processing_lineage=tuple(
                ProcessingStep.from_dict(cast(dict[str, Any], item)) for item in raw_lineage
            ),
        )

    def with_split(self, split: Split) -> ClipRecord:
        return replace(self, split=split)

    def to_dict(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "audio_path": self.audio_path,
            "audio_sha256": self.audio_sha256,
            "transcript": self.transcript,
            "language": self.language,
            "speaker_id": self.speaker_id,
            "consent_id": self.consent_id,
            "consent_status": self.consent_status,
            "source_license": self.source_license,
            "prompt_family_id": self.prompt_family_id,
            "split": self.split,
            "style": self.style,
            "processing_lineage": [step.to_dict() for step in self.processing_lineage],
        }


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    """A versioned collection of clip records."""

    dataset_id: str
    dataset_version: str
    clips: tuple[ClipRecord, ...]
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetManifest:
        schema_version = _required_string(data, "schema_version")
        if schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported schema_version {schema_version!r}; expected {SCHEMA_VERSION!r}"
            )
        raw_clips = data.get("clips")
        if not isinstance(raw_clips, list):
            raise ValueError("clips must be an array")
        if not all(isinstance(item, dict) for item in raw_clips):
            raise ValueError("every clips entry must be an object")
        return cls(
            schema_version=schema_version,
            dataset_id=_required_string(data, "dataset_id"),
            dataset_version=_required_string(data, "dataset_version"),
            clips=tuple(ClipRecord.from_dict(item) for item in raw_clips),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "clips": [clip.to_dict() for clip in self.clips],
        }


def load_manifest(path: Path) -> DatasetManifest:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest root must be an object")
    return DatasetManifest.from_dict(data)


def write_manifest(manifest: DatasetManifest, path: Path) -> None:
    path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
