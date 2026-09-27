"""Safe JSON, terminal, and static HTML reports for completed evaluation runs."""

from __future__ import annotations

import html
import json
import platform
import subprocess
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean, median
from typing import Any

from .dataset import TaskSuite
from .runner import EvaluationRecord

_SENSITIVE = {"authorization", "api_key", "apikey", "token", "password", "secret", "access_token", "refresh_token", "client_secret", "private_key"}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if key.lower() in _SENSITIVE else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    return value


def _percentile(values: list[float], fraction: float) -> float | None:
    if len(values) < 20:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower, upper = int(index), min(int(index) + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def summary(records: list[EvaluationRecord]) -> dict[str, Any]:
    total, passed = len(records), sum(record.passed for record in records)
    durations = [record.duration_ms for record in records]
    expected = [record for record in records if record.task.expected_tool is not None]
    tool_correct = sum(next((grade.passed for grade in record.grades if grade.grader == "tool_selection"), False) for record in expected)
    schema_records = [record for record in records if record.task.output_schema]
    schema_valid = sum(next((grade.passed for grade in record.grades if grade.grader == "structured_output"), False) for record in schema_records)
    forbidden = sum("forbidden_tool" in record.failure_types for record in records)
    costs = [record.result.estimated_cost_usd for record in records if record.result and record.result.estimated_cost_usd is not None]
    tokens = [record.result.normalized_total_tokens() for record in records if record.result and record.result.normalized_total_tokens() is not None]
    retries = [record.result.retry_count for record in records if record.result]
    failures = Counter(failure for record in records for failure in record.failure_types)
    category_records: dict[str, list[EvaluationRecord]] = {}
    for record in records:
        category_records.setdefault(record.task.category, []).append(record)
    per_category = {name: sum(record.passed for record in items) / len(items) for name, items in sorted(category_records.items())}
    workflows = [record for record in records if len(record.task.required_tools) >= 2]
    approval = [record for record in records if record.task.requires_approval]
    escalations = [record for record in records if record.task.requires_escalation]
    budgeted = [record for record in records if record.task.max_tool_calls is not None]
    recoveries = [record for record in records if isinstance(record.task.metadata.get("fault_plan"), dict) and record.result and record.result.structured_output and record.result.structured_output.get("resolution") == "recovered"]
    fault_tasks = [record for record in records if isinstance(record.task.metadata.get("fault_plan"), dict) and record.task.max_retries and record.task.max_retries > 0]
    successful_tool_counts = [len(record.result.tool_calls) for record in records if record.passed and record.result]

    def grade_pass(record: EvaluationRecord, grader: str) -> bool:
        return next((grade.passed for grade in record.grades if grade.grader == grader), False)

    return {
        "tasks_evaluated": total, "tasks_passed": passed, "task_success_rate": passed / total if total else None,
        "tool_accuracy": tool_correct / len(expected) if expected else None,
        "forbidden_tool_rate": forbidden / total if total else None,
        "structured_output_validity": schema_valid / len(schema_records) if schema_records else None,
        "average_latency_ms": fmean(durations) if durations else None, "p50_latency_ms": median(durations) if durations else None,
        "p95_latency_ms": _percentile(durations, 0.95), "fastest_latency_ms": min(durations) if durations else None,
        "slowest_latency_ms": max(durations) if durations else None, "retry_rate": sum(value > 0 for value in retries) / len(retries) if retries else None,
        "total_estimated_cost_usd": sum(costs) if costs else None, "average_cost_per_task_usd": fmean(costs) if costs else None,
        "total_tokens": sum(tokens) if tokens else None, "failure_distribution": dict(sorted(failures.items())),
        "category_success_rates": per_category,
        "workflow_success_rate": sum(record.passed for record in workflows) / len(workflows) if workflows else None,
        "approval_compliance": sum(grade_pass(record, "approval_boundary") for record in approval) / len(approval) if approval else None,
        "escalation_accuracy": sum(grade_pass(record, "escalation") for record in escalations) / len(escalations) if escalations else None,
        "unnecessary_tool_rate": sum(not grade_pass(record, "tool_call_budget") for record in budgeted) / len(budgeted) if budgeted else None,
        "recovery_rate": len(recoveries) / len(fault_tasks) if fault_tasks else None,
        "average_tool_calls_per_successful_task": fmean(successful_tool_counts) if successful_tool_counts else None,
    }


def build_report(records: list[EvaluationRecord], suite: TaskSuite | None = None) -> dict[str, Any]:
    from . import __version__
    return redact({
        "format_version": "1.0", "generated_at": datetime.now(UTC).isoformat(), "package_version": __version__,
        "git_commit": _git_commit(), "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "suite": ({"name": suite.name, "version": suite.version, "description": suite.description, "task_count": len(suite.tasks)} if suite else None), "summary": summary(records), "records": [asdict(record) for record in records],
    })


def write_json_report(path: Path, records: list[EvaluationRecord], suite: TaskSuite | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_report(records, suite), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_terminal(records: list[EvaluationRecord]) -> str:
    data = summary(records)
    def pct(value: float | None) -> str: return "N/A" if value is None else f"{value:.1%}"
    def number(value: float | None, unit: str = "") -> str: return "N/A" if value is None else f"{value:.2f}{unit}"
    lines = ["Agent Eval Lab", f"Tasks              {data['tasks_evaluated']}", f"Passed             {data['tasks_passed']}", f"Success rate       {pct(data['task_success_rate'])}", f"Tool accuracy      {pct(data['tool_accuracy'])}", f"Forbidden calls    {pct(data['forbidden_tool_rate'])}", f"Schema validity    {pct(data['structured_output_validity'])}", "Latency", f"p50                {number(data['p50_latency_ms'], ' ms')}", f"p95                {number(data['p95_latency_ms'], ' ms')}", f"Average            {number(data['average_latency_ms'], ' ms')}", f"Estimated cost     {('N/A' if data['total_estimated_cost_usd'] is None else '$' + format(data['total_estimated_cost_usd'], '.6f'))}"]
    if data["failure_distribution"]:
        lines.append("Failures")
        lines.extend(f"{kind:<20} {count}" for kind, count in data["failure_distribution"].items())
    domain_metrics = (("Workflow success", data["workflow_success_rate"]), ("Approval compliance", data["approval_compliance"]), ("Escalation accuracy", data["escalation_accuracy"]), ("Unnecessary tool rate", data["unnecessary_tool_rate"]), ("Recovery rate", data["recovery_rate"]))
    observed = [(label, value) for label, value in domain_metrics if value is not None]
    if observed:
        lines.append("Workflow controls")
        lines.extend(f"{label:<22} {pct(value)}" for label, value in observed)
    return "\n".join(lines)


def write_html_report(path: Path, records: list[EvaluationRecord], suite: TaskSuite | None = None) -> None:
    report, data = build_report(records, suite), summary(records)
    rows = "".join(f"<tr><td>{html.escape(record.task_id)}</td><td>{'PASS' if record.passed else 'FAIL'}</td><td>{record.duration_ms:.2f}</td><td>{html.escape(', '.join(record.failure_types) or '—')}</td><td>{html.escape(' | '.join(grade.reason for grade in record.grades if not grade.passed) or '—')}</td></tr>" for record in records)
    metrics = "".join(f"<div class=metric><b>{html.escape(key.replace('_', ' '))}</b><span>{html.escape(str(value if value is not None else 'N/A'))}</span></div>" for key, value in data.items() if key not in {"failure_distribution", "category_success_rates"})
    failures = "".join(f"<li>{html.escape(kind)}: {count}</li>" for kind, count in data["failure_distribution"].items()) or "<li>No failures recorded.</li>"
    categories = "".join(f"<li>{html.escape(category)}: {rate:.1%}</li>" for category, rate in data["category_success_rates"].items())
    rows = "".join(f"<tr><td>{html.escape(record.task_id)}</td><td>{html.escape(record.task.category)}</td><td>{'PASS' if record.passed else 'FAIL'}</td><td>{html.escape(' → '.join(call.name for call in (record.result.tool_calls if record.result else ())) or '—')}</td><td>{record.duration_ms:.2f}</td><td>{html.escape(', '.join(record.failure_types) or '—')}</td><td>{html.escape(' | '.join(grade.reason for grade in record.grades if not grade.passed) or '—')}</td></tr>" for record in records)
    document = f"""<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Agent Eval Lab report</title><style>body{{font:15px system-ui,sans-serif;margin:2rem;color:#17221b;background:#fbfcfa}}main{{max-width:1280px;margin:auto}}h1{{margin-bottom:.2rem}}.meta{{color:#536057}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.7rem}}.metric,table{{background:#fff;border:1px solid #d9e1da;border-radius:8px;padding:.8rem}}.metric b,.metric span{{display:block}}.metric b{{text-transform:capitalize;font-size:.8rem;color:#536057}}.metric span{{font-size:1.1rem;margin-top:.25rem}}table{{border-collapse:collapse;width:100%;padding:0;overflow:hidden}}th,td{{padding:.7rem;text-align:left;border-bottom:1px solid #e5ebe5;vertical-align:top}}th{{background:#f2f6f1}}@media(max-width:650px){{body{{margin:1rem}}table{{font-size:.82rem}}}}</style><main><h1>Agent Eval Lab</h1><p class=meta>Static evaluation report · generated {html.escape(report['generated_at'])} · deterministic report rendering</p><h2>Summary</h2><section class=metrics>{metrics}</section><h2>Category success</h2><ul>{categories}</ul><h2>Failure analysis</h2><ul>{failures}</ul><h2>Tasks</h2><table><thead><tr><th>Task</th><th>Category</th><th>Status</th><th>Trajectory</th><th>Latency (ms)</th><th>Failure type</th><th>Grader detail</th></tr></thead><tbody>{rows}</tbody></table></main></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
