"""Explicit, direction-aware regression gates for evaluation reports."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping


class PolicyValidationError(ValueError):
    """Raised when a regression policy is ambiguous or semantically invalid."""


HIGHER_IS_BETTER = "higher_is_better"
LOWER_IS_BETTER = "lower_is_better"

# Metrics intentionally eligible for relative regression gates. Count and total
# metrics are excluded because their meaning changes with suite size or telemetry.
COMPARABLE_METRICS: dict[str, str] = {
    "task_success_rate": HIGHER_IS_BETTER,
    "tool_accuracy": HIGHER_IS_BETTER,
    "structured_output_validity": HIGHER_IS_BETTER,
    "forbidden_tool_rate": LOWER_IS_BETTER,
    "average_latency_ms": LOWER_IS_BETTER,
    "p50_latency_ms": LOWER_IS_BETTER,
    "p95_latency_ms": LOWER_IS_BETTER,
    "retry_rate": LOWER_IS_BETTER,
    "average_cost_per_task_usd": LOWER_IS_BETTER,
}


@dataclass(frozen=True)
class GateResult:
    metric: str
    passed: bool
    baseline: float | None
    candidate: float | None
    reason: str


DEFAULT_POLICY: dict[str, dict[str, float | str]] = {
    "task_success_rate": {"direction": HIGHER_IS_BETTER, "max_regression": 0.02},
    "forbidden_tool_rate": {"max": 0.0},
}


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise PolicyValidationError(f"{label} must be a finite number.")
    return float(value)


def _validate_rule(metric: str, raw_rule: Any) -> tuple[str, float]:
    if not isinstance(raw_rule, Mapping):
        raise PolicyValidationError(f"Policy for {metric!r} must be an object.")
    has_max, has_regression = "max" in raw_rule, "max_regression" in raw_rule
    if has_max == has_regression:
        raise PolicyValidationError(f"Policy for {metric!r} must contain exactly one of 'max' or 'max_regression'.")
    unexpected = set(raw_rule) - ({"max"} if has_max else {"direction", "max_regression"})
    if unexpected:
        raise PolicyValidationError(f"Policy for {metric!r} has unsupported keys: {', '.join(sorted(unexpected))}.")
    if has_max:
        return "max", _number(raw_rule["max"], f"Policy max for {metric!r}")

    expected_direction = COMPARABLE_METRICS.get(metric)
    if expected_direction is None:
        raise PolicyValidationError(f"Metric {metric!r} is not eligible for relative regression gates.")
    direction = raw_rule.get("direction")
    if direction not in {HIGHER_IS_BETTER, LOWER_IS_BETTER}:
        raise PolicyValidationError(f"Policy direction for {metric!r} must be '{HIGHER_IS_BETTER}' or '{LOWER_IS_BETTER}'.")
    if direction != expected_direction:
        raise PolicyValidationError(f"Policy direction for {metric!r} must be '{expected_direction}'.")
    tolerance = _number(raw_rule["max_regression"], f"Policy max_regression for {metric!r}")
    if tolerance < 0:
        raise PolicyValidationError(f"Policy max_regression for {metric!r} cannot be negative.")
    return direction, tolerance


def compare_reports(
    baseline: Mapping[str, Any], candidate: Mapping[str, Any], policy: Mapping[str, Any] = DEFAULT_POLICY,
) -> list[GateResult]:
    """Compare reports using a validated policy without assuming metric direction.

    A relative gate compares a candidate to its tolerated boundary, rather than
    dividing by the baseline. This makes zero baselines well-defined: a zero
    forbidden-action rate may not rise, while a zero success rate may improve.
    """
    if not isinstance(policy, Mapping) or not policy:
        raise PolicyValidationError("Regression policy must be a non-empty object.")
    before, after = baseline.get("summary", {}), candidate.get("summary", {})
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        raise PolicyValidationError("Both reports must contain a summary object.")

    results: list[GateResult] = []
    for metric, raw_rule in policy.items():
        if not isinstance(metric, str):
            raise PolicyValidationError("Regression policy metric names must be strings.")
        mode, limit = _validate_rule(metric, raw_rule)
        old, new = before.get(metric), after.get(metric)
        if old is None or new is None:
            results.append(GateResult(metric, False, None, None, "Metric is unavailable in one or both reports."))
            continue
        old_value, new_value = _number(old, f"Baseline metric {metric!r}"), _number(new, f"Candidate metric {metric!r}")
        if mode == "max":
            passed = new_value <= limit + 1e-12
            reason = f"Candidate must be <= {limit:g}."
        elif mode == HIGHER_IS_BETTER:
            boundary = old_value * (1 - limit)
            passed = new_value + 1e-12 >= boundary
            reason = f"Higher is better; candidate must be >= {boundary:g} (at most {limit:.1%} regression)."
        else:
            boundary = old_value * (1 + limit)
            passed = new_value <= boundary + 1e-12
            reason = f"Lower is better; candidate must be <= {boundary:g} (at most {limit:.1%} regression)."
        results.append(GateResult(metric, passed, old_value, new_value, reason))
    return results
