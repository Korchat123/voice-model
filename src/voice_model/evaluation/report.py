"""Versioned machine-readable evaluation reports."""

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class MetricStatus(StrEnum):
    MEASURED = "measured"
    NOT_MEASURED = "not_measured"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class MetricResult:
    status: MetricStatus
    value: float | int | bool | None = None
    unit: str | None = None
    reason: str | None = None
    adapter_id: str | None = None
    model_revision: str | None = None

    def __post_init__(self) -> None:
        if self.status is MetricStatus.MEASURED and self.value is None:
            raise ValueError("measured metric requires a value")
        if self.status is MetricStatus.NOT_MEASURED and not self.reason:
            raise ValueError("unmeasured metric requires a reason")
        if (self.adapter_id is None) != (self.model_revision is None):
            raise ValueError("adapter ID and model revision must be recorded together")


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    schema_version: int
    run_id: str
    config_version: str
    project_revision: str
    dataset_revision: str
    engine_id: str
    model_id: str
    model_version: str
    language: str
    metrics: dict[str, MetricResult]

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported evaluation report schema")
        required = (
            self.run_id,
            self.config_version,
            self.project_revision,
            self.dataset_revision,
            self.engine_id,
            self.model_id,
            self.model_version,
        )
        if any(not item or item.startswith("UNSET") for item in required):
            raise ValueError("report provenance must use concrete immutable revisions")
        if self.language not in {"th", "en", "mixed"}:
            raise ValueError("report language must be th, en, or mixed")

    def to_json(self) -> str:
        payload: dict[str, Any] = asdict(self)
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    def write(self, path: Path) -> None:
        path.write_text(self.to_json(), encoding="utf-8")
