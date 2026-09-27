"""Composable deterministic graders; semantic judges remain optional extensions."""

from __future__ import annotations

from typing import Protocol

from .contracts import AgentResult, GradeResult, Task


class Grader(Protocol):
    name: str
    def grade(self, task: Task, result: AgentResult, duration_ms: float, error: str | None) -> GradeResult: ...


def _pass(name: str, reason: str, **metadata: object) -> GradeResult:
    return GradeResult(name, True, 1.0, reason, metadata=metadata)


def _fail(name: str, reason: str, failure_type: str, **metadata: object) -> GradeResult:
    return GradeResult(name, False, 0.0, reason, failure_type, metadata=metadata)


class ToolSelectionGrader:
    name = "tool_selection"
    def grade(self, task: Task, result: AgentResult, duration_ms: float, error: str | None) -> GradeResult:
        called = [call.name for call in result.tool_calls]
        if task.expected_tool is None:
            return _pass(self.name, "No tool was required and none was called.") if not called else _fail(self.name, f"No tool was required; called {called!r}.", "unexpected_tool", called_tools=called)
        return _pass(self.name, f"Expected tool {task.expected_tool!r} was called.") if task.expected_tool in called else _fail(self.name, f"Expected {task.expected_tool!r}; called {called!r}.", "wrong_tool", called_tools=called)


class AllowedToolGrader:
    name = "allowed_tools"
    def grade(self, task: Task, result: AgentResult, duration_ms: float, error: str | None) -> GradeResult:
        if not task.allowed_tools:
            return _pass(self.name, "No allow-list is configured.")
        violations = sorted({call.name for call in result.tool_calls if call.name not in task.allowed_tools})
        return _pass(self.name, "All tool calls are allowed.") if not violations else _fail(self.name, f"Called tools outside the allow-list: {violations!r}.", "forbidden_tool", violations=violations)


class ForbiddenToolGrader:
    name = "forbidden_tools"
    def grade(self, task: Task, result: AgentResult, duration_ms: float, error: str | None) -> GradeResult:
        violations = sorted({call.name for call in result.tool_calls if call.name in task.forbidden_tools})
        return _pass(self.name, "No forbidden tool was called.") if not violations else _fail(self.name, f"Forbidden tools called: {violations!r}.", "forbidden_tool", violations=violations)


class RequiredFieldsGrader:
    name = "required_fields"
    def grade(self, task: Task, result: AgentResult, duration_ms: float, error: str | None) -> GradeResult:
        missing = [field for field in task.required_output_fields if field not in (result.structured_output or {})]
        return _pass(self.name, "All required output fields are present.") if not missing else _fail(self.name, f"Missing required fields: {missing!r}.", "invalid_output", missing=missing)


class StructuredOutputGrader:
    name = "structured_output"
    _types = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "object": dict, "array": list}
    def grade(self, task: Task, result: AgentResult, duration_ms: float, error: str | None) -> GradeResult:
        if not task.output_schema:
            return _pass(self.name, "No output schema is configured.")
        output = result.structured_output
        if output is None:
            return _fail(self.name, "Structured output was not supplied.", "schema_violation")
        invalid: list[str] = []
        for field, expected in task.output_schema.items():
            value, expected_type = output.get(field), self._types.get(expected)
            if expected_type is None or field not in output or not isinstance(value, expected_type) or (expected == "integer" and isinstance(value, bool)):
                invalid.append(field)
        return _pass(self.name, "Structured output satisfies the configured schema.") if not invalid else _fail(self.name, f"Fields do not satisfy schema: {invalid!r}.", "schema_violation", invalid=invalid)


class LatencyBudgetGrader:
    name = "latency_budget"
    def grade(self, task: Task, result: AgentResult, duration_ms: float, error: str | None) -> GradeResult:
        if task.max_latency_ms is None:
            return _pass(self.name, "No latency budget is configured.")
        return _pass(self.name, f"{duration_ms:.2f} ms is within budget.", budget_ms=task.max_latency_ms) if duration_ms <= task.max_latency_ms else _fail(self.name, f"{duration_ms:.2f} ms exceeds {task.max_latency_ms:.2f} ms.", "timeout", budget_ms=task.max_latency_ms)


class RetryBudgetGrader:
    name = "retry_budget"
    def grade(self, task: Task, result: AgentResult, duration_ms: float, error: str | None) -> GradeResult:
        if task.max_retries is None:
            return _pass(self.name, "No retry budget is configured.")
        return _pass(self.name, f"Retry count {result.retry_count} is within budget.") if result.retry_count <= task.max_retries else _fail(self.name, f"Retry count {result.retry_count} exceeds budget {task.max_retries}.", "retry_exhausted")


class ErrorBehaviorGrader:
    name = "error_behavior"
    def grade(self, task: Task, result: AgentResult, duration_ms: float, error: str | None) -> GradeResult:
        message = error or "; ".join(result.errors)
        return _pass(self.name, "No execution error was captured.") if not message else _fail(self.name, f"Agent execution reported an error: {message}", "provider_error")


DEFAULT_GRADERS: tuple[Grader, ...] = (ToolSelectionGrader(), AllowedToolGrader(), ForbiddenToolGrader(), RequiredFieldsGrader(), StructuredOutputGrader(), LatencyBudgetGrader(), RetryBudgetGrader(), ErrorBehaviorGrader())
