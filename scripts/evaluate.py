"""Measure a PCM WAV and create a provenance-complete evaluation report."""

import argparse
from pathlib import Path

from voice_model.evaluation import (
    EvaluationReport,
    MetricResult,
    MetricStatus,
    measure_wav,
)
from voice_model.evaluation.adapters import unavailable_reason


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--config-version", default="1.0.0")
    parser.add_argument("--project-revision", required=True)
    parser.add_argument("--dataset-revision", required=True)
    parser.add_argument("--engine-id", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--language", choices=("th", "en", "mixed"), required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audio = measure_wav(args.audio)
    metrics = {
        f"audio.{name}": MetricResult(MetricStatus.MEASURED, value, _unit(name))
        for name, value in audio.as_dict().items()
    }
    metrics["intelligibility.asr_error_rate"] = MetricResult(
        MetricStatus.NOT_MEASURED,
        reason=unavailable_reason("ASR intelligibility"),
    )
    metrics["speaker.similarity"] = MetricResult(
        MetricStatus.NOT_MEASURED,
        reason=unavailable_reason("speaker similarity"),
    )
    report = EvaluationReport(
        schema_version=1,
        run_id=args.run_id,
        config_version=args.config_version,
        project_revision=args.project_revision,
        dataset_revision=args.dataset_revision,
        engine_id=args.engine_id,
        model_id=args.model_id,
        model_version=args.model_version,
        language=args.language,
        metrics=metrics,
    )
    report.write(args.output)
    return 0


def _unit(name: str) -> str | None:
    if name.endswith("_ms"):
        return "ms"
    if name.endswith("_dbfs"):
        return "dBFS"
    if name.endswith("_hz"):
        return "Hz"
    if name == "silence_ratio":
        return "ratio"
    return None


if __name__ == "__main__":
    raise SystemExit(main())
