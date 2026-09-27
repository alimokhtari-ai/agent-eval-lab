from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from .contracts import AgentAdapter, AgentResult, Task
from .graders import contract_passed, latency_passed, tool_selection_passed


@dataclass(frozen=True)
class EvaluationRecord:
    task_id: str
    duration_ms: float
    tool_selection_passed: bool
    contract_passed: bool
    latency_passed: bool
    error: str | None
    result: AgentResult | None

    @property
    def passed(self) -> bool:
        return self.error is None and all(
            (self.tool_selection_passed, self.contract_passed, self.latency_passed)
        )


def evaluate_task(adapter: AgentAdapter, task: Task) -> EvaluationRecord:
    started = perf_counter()
    try:
        result = adapter.run(task)
    except Exception as exc:  # adapters are untrusted integration boundaries
        return EvaluationRecord(
            task_id=task.id,
            duration_ms=(perf_counter() - started) * 1000,
            tool_selection_passed=False,
            contract_passed=False,
            latency_passed=False,
            error=f"{type(exc).__name__}: {exc}",
            result=None,
        )

    duration_ms = (perf_counter() - started) * 1000
    return EvaluationRecord(
        task_id=task.id,
        duration_ms=duration_ms,
        tool_selection_passed=tool_selection_passed(task, result),
        contract_passed=contract_passed(task, result),
        latency_passed=latency_passed(task, duration_ms),
        error=None,
        result=result,
    )


def evaluate_tasks(adapter: AgentAdapter, tasks: list[Task]) -> list[EvaluationRecord]:
    return [evaluate_task(adapter, task) for task in tasks]
