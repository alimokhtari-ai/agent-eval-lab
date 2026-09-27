from __future__ import annotations

import unittest

from agent_eval_lab.regression import (
    HIGHER_IS_BETTER,
    LOWER_IS_BETTER,
    PolicyValidationError,
    compare_reports,
)


def report(**summary: float | None) -> dict[str, dict[str, float | None]]:
    return {"summary": summary}


class RegressionTests(unittest.TestCase):
    def test_higher_metric_passes_at_threshold(self) -> None:
        gates = compare_reports(report(task_success_rate=1.0), report(task_success_rate=0.98), {"task_success_rate": {"direction": HIGHER_IS_BETTER, "max_regression": 0.02}})
        self.assertTrue(gates[0].passed)

    def test_higher_metric_fails_below_threshold(self) -> None:
        gates = compare_reports(report(task_success_rate=1.0), report(task_success_rate=0.979), {"task_success_rate": {"direction": HIGHER_IS_BETTER, "max_regression": 0.02}})
        self.assertFalse(gates[0].passed)

    def test_lower_metric_uses_increasing_boundary(self) -> None:
        policy = {"p95_latency_ms": {"direction": LOWER_IS_BETTER, "max_regression": 0.20}}
        self.assertTrue(compare_reports(report(p95_latency_ms=100.0), report(p95_latency_ms=120.0), policy)[0].passed)
        self.assertFalse(compare_reports(report(p95_latency_ms=100.0), report(p95_latency_ms=120.1), policy)[0].passed)

    def test_zero_baseline_is_well_defined(self) -> None:
        policy = {"forbidden_tool_rate": {"direction": LOWER_IS_BETTER, "max_regression": 0.20}}
        self.assertTrue(compare_reports(report(forbidden_tool_rate=0.0), report(forbidden_tool_rate=0.0), policy)[0].passed)
        self.assertFalse(compare_reports(report(forbidden_tool_rate=0.0), report(forbidden_tool_rate=0.01), policy)[0].passed)

    def test_absolute_max_is_useful_for_zero_tolerance(self) -> None:
        policy = {"forbidden_tool_rate": {"max": 0.0}}
        self.assertFalse(compare_reports(report(forbidden_tool_rate=0.0), report(forbidden_tool_rate=0.1), policy)[0].passed)

    def test_missing_metric_fails_gate_without_crashing(self) -> None:
        gate = compare_reports(report(task_success_rate=1.0), report(), {"task_success_rate": {"direction": HIGHER_IS_BETTER, "max_regression": 0.02}})[0]
        self.assertFalse(gate.passed)
        self.assertIn("unavailable", gate.reason)

    def test_invalid_direction_is_rejected(self) -> None:
        with self.assertRaises(PolicyValidationError):
            compare_reports(report(p95_latency_ms=1), report(p95_latency_ms=1), {"p95_latency_ms": {"direction": HIGHER_IS_BETTER, "max_regression": 0.1}})

    def test_ambiguous_rule_is_rejected(self) -> None:
        with self.assertRaises(PolicyValidationError):
            compare_reports(report(task_success_rate=1), report(task_success_rate=1), {"task_success_rate": {"max": 1, "max_regression": 0.1}})
