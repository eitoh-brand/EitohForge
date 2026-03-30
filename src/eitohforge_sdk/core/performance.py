"""Performance baseline helpers and regression checks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True)
class BenchmarkMetric:
    """Metric for one benchmark operation."""

    name: str
    iterations: int
    total_ms: float
    avg_ms: float


def run_micro_benchmarks(
    cases: dict[str, Callable[[], object]],
    *,
    iterations: int = 500,
) -> dict[str, BenchmarkMetric]:
    """Run in-process micro benchmarks for deterministic baselines."""
    results: dict[str, BenchmarkMetric] = {}
    safe_iterations = max(1, iterations)
    for name, case in cases.items():
        started = perf_counter()
        for _ in range(safe_iterations):
            case()
        total_ms = (perf_counter() - started) * 1000.0
        results[name] = BenchmarkMetric(
            name=name,
            iterations=safe_iterations,
            total_ms=total_ms,
            avg_ms=total_ms / safe_iterations,
        )
    return results


def detect_regressions(
    current: dict[str, BenchmarkMetric],
    baseline: dict[str, BenchmarkMetric],
    *,
    max_regression_percent: float = 20.0,
) -> dict[str, float]:
    """Return percentage regressions for metrics that exceed threshold."""
    regressions: dict[str, float] = {}
    threshold = max(0.0, max_regression_percent)
    for name, current_metric in current.items():
        baseline_metric = baseline.get(name)
        if baseline_metric is None or baseline_metric.avg_ms <= 0:
            continue
        regression = ((current_metric.avg_ms - baseline_metric.avg_ms) / baseline_metric.avg_ms) * 100.0
        if regression > threshold:
            regressions[name] = regression
    return regressions
