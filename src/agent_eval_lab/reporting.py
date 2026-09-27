from __future__ import annotations

from statistics import fmean

from .runner import EvaluationRecord


def summary(records: list[EvaluationRecord]) -> dict[str, object]:
    total = len(records)
    passed = sum(record.passed for record in records)
    measured_costs = [record.result.estimated_cost_usd for record in records if record.result and record.result.estimated_cost_usd is not None]
    return {
        "tasks_evaluated": total,
        "tasks_passed": passed,
        "task_success_rate": (passed / total) if total else 0.0,
        "average_latency_ms": fmean(record.duration_ms for record in records) if records else 0.0,
        "total_estimated_cost_usd": sum(measured_costs) if measured_costs else None,
        "cost_telemetry_available": bool(measured_costs),
    }


def render_terminal(records: list[EvaluationRecord]) -> str:
    data = summary(records)
    cost = f"${data['total_estimated_cost_usd']:.6f}" if data["cost_telemetry_available"] else "not reported by this adapter"
    lines = [
        f"Tasks evaluated: {data['tasks_evaluated']}",
        f"Tasks passed: {data['tasks_passed']}",
        f"Task success rate: {data['task_success_rate']:.1%}",
        f"Average latency: {data['average_latency_ms']:.2f} ms",
        f"Token and cost telemetry: {cost}",
    ]
    for record in records:
        lines.append(f"- {record.task_id}: {'PASS' if record.passed else 'FAIL'}")
    return "\n".join(lines)
