"""Transparent CI-friendly comparison of two JSON evaluation reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GateResult:
    metric: str
    passed: bool
    baseline: float | None
    candidate: float | None
    reason: str


DEFAULT_POLICY: dict[str, dict[str, float]] = {
    "task_success_rate": {"max_regression": 0.02},
    "forbidden_tool_rate": {"max": 0.0},
}


def compare_reports(baseline: dict[str, Any], candidate: dict[str, Any], policy: dict[str, dict[str, float]] = DEFAULT_POLICY) -> list[GateResult]:
    before, after = baseline.get("summary", {}), candidate.get("summary", {})
    results: list[GateResult] = []
    for metric, rule in policy.items():
        old, new = before.get(metric), after.get(metric)
        if old is None or new is None:
            results.append(GateResult(metric, False, old, new, "Metric is unavailable in one or both reports."))
            continue
        if "max" in rule:
            passed = new <= rule["max"]
            results.append(GateResult(metric, passed, old, new, f"Candidate must be <= {rule['max']}."))
        else:
            regression = (new - old) / old if old else (0.0 if new == old else float("inf"))
            passed = regression >= -rule["max_regression"] - 1e-12
            results.append(GateResult(metric, passed, old, new, f"Regression must not exceed {rule['max_regression']:.1%}."))
    return results
