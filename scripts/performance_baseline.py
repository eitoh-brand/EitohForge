"""Generate/check performance baseline metrics."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path

from eitohforge_sdk.core import (
    BenchmarkMetric,
    FeatureFlagDefinition,
    FeatureFlagService,
    FeatureFlagTargetingContext,
    JwtTokenManager,
    detect_regressions,
    run_micro_benchmarks,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Performance baseline runner.")
    parser.add_argument("--mode", choices=("baseline", "check"), default="baseline")
    parser.add_argument("--output", default="docs/performance/baseline.json")
    parser.add_argument("--threshold", type=float, default=25.0)
    args = parser.parse_args()

    metrics = _run_suite()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "metrics": {
            name: {
                "iterations": metric.iterations,
                "total_ms": round(metric.total_ms, 4),
                "avg_ms": round(metric.avg_ms, 6),
            }
            for name, metric in metrics.items()
        },
    }

    if args.mode == "baseline":
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        _write_markdown_summary(output_path.with_suffix(".md"), payload)
        return 0

    if not output_path.exists():
        raise SystemExit(f"Baseline file not found: {output_path}")
    baseline_payload = json.loads(output_path.read_text(encoding="utf-8"))
    baseline_metrics = {
        name: _metric_from_payload(name, metric_payload)
        for name, metric_payload in baseline_payload.get("metrics", {}).items()
    }
    regressions = detect_regressions(metrics, baseline_metrics, max_regression_percent=args.threshold)
    if regressions:
        details = ", ".join(f"{name}={value:.2f}%" for name, value in sorted(regressions.items()))
        raise SystemExit(f"Performance regression detected: {details}")
    print("Performance check passed.")
    return 0


def _run_suite() -> dict[str, BenchmarkMetric]:
    jwt_manager = JwtTokenManager(secret="x" * 32)
    pair = jwt_manager.issue_token_pair(subject="perf-user", tenant_id="tenant-a")
    flag_service = FeatureFlagService()
    flag_service.register(FeatureFlagDefinition(key="perf-flag", rollout_percentage=50))
    context = FeatureFlagTargetingContext(actor_id="actor-1", tenant_id="tenant-a")
    return run_micro_benchmarks(
        {
            "jwt.decode_access": lambda: jwt_manager.decode_and_validate(pair.access_token),
            "feature_flags.evaluate": lambda: flag_service.evaluate("perf-flag", context=context),
        },
        iterations=1000,
    )


def _metric_from_payload(name: str, payload: dict[str, object]) -> BenchmarkMetric:
    return BenchmarkMetric(
        name=name,
        iterations=int(payload.get("iterations", 1)),
        total_ms=float(payload.get("total_ms", 0.0)),
        avg_ms=float(payload.get("avg_ms", 0.0)),
    )


def _write_markdown_summary(path: Path, payload: dict[str, object]) -> None:
    metrics = payload.get("metrics", {})
    lines = [
        "# Performance Baseline",
        "",
        f"Generated at: `{payload.get('generated_at')}`",
        "",
        "| Metric | Iterations | Avg (ms) | Total (ms) |",
        "|---|---:|---:|---:|",
    ]
    if isinstance(metrics, dict):
        for name, value in sorted(metrics.items()):
            if not isinstance(value, dict):
                continue
            lines.append(
                f"| `{name}` | {value.get('iterations', 0)} | {value.get('avg_ms', 0)} | {value.get('total_ms', 0)} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
