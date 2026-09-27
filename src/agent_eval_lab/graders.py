from __future__ import annotations

from .contracts import AgentResult, Task


def tool_selection_passed(task: Task, result: AgentResult) -> bool:
    return any(call.name == task.expected_tool for call in result.tool_calls)


def contract_passed(task: Task, result: AgentResult) -> bool:
    return all(key in result.structured_output for key in task.required_output_keys)


def latency_passed(task: Task, duration_ms: float) -> bool:
    return duration_ms <= task.max_latency_ms
