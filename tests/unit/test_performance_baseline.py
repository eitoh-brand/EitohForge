from __future__ import annotations

import pytest

from eitohforge_sdk.core.performance import BenchmarkMetric, detect_regressions, run_micro_benchmarks

pytestmark = pytest.mark.perf


def test_run_micro_benchmarks_returns_metrics() -> None:
    counter = {"value": 0}

    def inc() -> None:
        counter["value"] += 1

    result = run_micro_benchmarks({"inc": inc}, iterations=10)
    assert "inc" in result
    assert result["inc"].iterations == 10
    assert counter["value"] == 10


def test_detect_regressions_flags_above_threshold_only() -> None:
    baseline = {"a": BenchmarkMetric(name="a", iterations=10, total_ms=10.0, avg_ms=1.0)}
    current = {"a": BenchmarkMetric(name="a", iterations=10, total_ms=15.0, avg_ms=1.5)}
    regressions = detect_regressions(current, baseline, max_regression_percent=20.0)
    assert "a" in regressions
    assert regressions["a"] > 20.0
