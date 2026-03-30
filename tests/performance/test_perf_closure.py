"""Performance baseline smoke checks (CI-friendly, no external services)."""

from __future__ import annotations

import pytest

from eitohforge_sdk.core.performance import BenchmarkMetric, detect_regressions, run_micro_benchmarks


@pytest.mark.perf
def test_micro_benchmark_suite_runs_under_budget() -> None:
    counter = {"n": 0}

    def work() -> None:
        counter["n"] += 1

    metrics = run_micro_benchmarks({"noop": work}, iterations=200)
    metric = metrics["noop"]
    assert metric.iterations == 200
    assert metric.avg_ms < 25.0, f"avg_ms too high for CI stability: {metric.avg_ms}"

    baseline = {"noop": BenchmarkMetric(name="noop", iterations=200, total_ms=200.0, avg_ms=1.0)}
    current = {"noop": BenchmarkMetric(name="noop", iterations=200, total_ms=metric.total_ms, avg_ms=metric.avg_ms)}
    assert detect_regressions(current, baseline, max_regression_percent=500.0) == {}
