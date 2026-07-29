import pytest

from voice_model.evaluation import (
    CancellationMetrics,
    ControlMonotonicity,
    EvaluationReport,
    LatencyMetrics,
    MetricResult,
    MetricStatus,
    error_rate,
)


def test_latency_and_rtf_use_nearest_rank_p95() -> None:
    result = LatencyMetrics.from_samples(
        [100.0, 200.0, 300.0],
        [500.0, 1000.0, 1500.0],
        [1000.0, 2000.0, 3000.0],
    )
    assert result.first_audio_median_ms == 200.0
    assert result.first_audio_p95_ms == 300.0
    assert result.rtf_p95 == 0.5


def test_cancellation_summary() -> None:
    result = CancellationMetrics.from_samples([25.0, 50.0, 100.0])
    assert result.median_ms == 50.0
    assert result.p95_ms == 100.0


def test_control_monotonicity_reports_failure_without_hiding_values() -> None:
    result = ControlMonotonicity.evaluate("resonance", [-1.0, 0.0, 1.0], [0.1, 0.3, 0.2])
    assert not result.monotonic
    assert result.observations == (0.1, 0.3, 0.2)


def test_error_rate_uses_adapter_transcript_tokens() -> None:
    assert error_rate(list("cat"), list("cut")) == pytest.approx(1 / 3)
    assert error_rate(["hello", "world"], ["hello"]) == 0.5


def test_unmeasured_metric_requires_reason() -> None:
    with pytest.raises(ValueError, match="reason"):
        MetricResult(MetricStatus.NOT_MEASURED)


def test_report_rejects_unset_provenance() -> None:
    with pytest.raises(ValueError, match="provenance"):
        EvaluationReport(
            schema_version=1,
            run_id="run-1",
            config_version="1",
            project_revision="UNSET",
            dataset_revision="dataset-sha",
            engine_id="fake",
            model_id="fake",
            model_version="1",
            language="th",
            metrics={},
        )
