"""Execution runtime: visible failures, bounded retries, deterministic ordering."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Iterable

from .contracts import AgentAdapter, AgentResult, GradeResult, RetryableAgentError, Task
from .graders import DEFAULT_GRADERS, Grader


@dataclass(frozen=True)
class EvaluationRecord:
    task: Task
    duration_ms: float
    result: AgentResult | None
    grades: tuple[GradeResult, ...]
    error: str | None = None
    attempts: int = 1

    @property
    def task_id(self) -> str:
        return self.task.id

    @property
    def passed(self) -> bool:
        return self.error is None and bool(self.result) and all(grade.passed for grade in self.grades)

    @property
    def failure_types(self) -> tuple[str, ...]:
        failures = [grade.failure_type for grade in self.grades if grade.failure_type]
        if self.error and not failures:
            failures.append("provider_error")
        return tuple(dict.fromkeys(failures))


def _error_record(task: Task, duration_ms: float, error: str, attempts: int) -> EvaluationRecord:
    result = AgentResult(errors=(error,), retry_count=max(attempts - 1, 0))
    grades = tuple(grader.grade(task, result, duration_ms, error) for grader in DEFAULT_GRADERS)
    return EvaluationRecord(task, duration_ms, result, grades, error, attempts)


def evaluate_task(adapter: AgentAdapter, task: Task, graders: Iterable[Grader] = DEFAULT_GRADERS) -> EvaluationRecord:
    started, attempts = perf_counter(), 0
    retry_budget = task.max_retries or 0
    while True:
        attempts += 1
        try:
            result = adapter.run(task)
            break
        except RetryableAgentError as exc:
            if attempts <= retry_budget:
                continue
            duration_ms = (perf_counter() - started) * 1000
            return _error_record(task, duration_ms, f"retry_exhausted: {type(exc).__name__}: {exc}", attempts)
        except Exception as exc:  # adapter integrations are intentionally untrusted boundaries
            duration_ms = (perf_counter() - started) * 1000
            return _error_record(task, duration_ms, f"provider_error: {type(exc).__name__}: {exc}", attempts)
    duration_ms = (perf_counter() - started) * 1000
    # Adapter retries and runner retries are both visible in a single normalized count.
    if attempts > 1:
        result = AgentResult(**{**result.__dict__, "retry_count": result.retry_count + attempts - 1})
    grade_results = tuple(grader.grade(task, result, duration_ms, None) for grader in graders)
    return EvaluationRecord(task, duration_ms, result, grade_results, None, attempts)


def evaluate_tasks(adapter: AgentAdapter, tasks: list[Task], graders: Iterable[Grader] = DEFAULT_GRADERS) -> list[EvaluationRecord]:
    return [evaluate_task(adapter, task, graders) for task in tasks]
