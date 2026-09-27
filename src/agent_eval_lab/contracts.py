"""Provider-neutral domain contracts for agent evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Mapping[str, JsonValue] = field(default_factory=dict)
    succeeded: bool | None = None
    error: str | None = None
    sequence: int | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class Task:
    id: str
    input: str
    category: str
    expected_tool: str | None = None
    allowed_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    required_output_fields: tuple[str, ...] = ()
    output_schema: Mapping[str, str] = field(default_factory=dict)
    max_latency_ms: float | None = None
    timeout_seconds: float | None = None
    max_retries: int | None = None
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)
    required_tools: tuple[str, ...] = ()
    expected_tool_sequence: tuple[str, ...] = ()
    max_tool_calls: int | None = None
    requires_approval: bool = False
    requires_escalation: bool = False

    @property
    def prompt(self) -> str:
        return self.input


@dataclass(frozen=True)
class AgentResult:
    final_output: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    structured_output: Mapping[str, JsonValue] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    retry_count: int = 0
    provider: str | None = None
    model: str | None = None
    errors: tuple[str, ...] = ()
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def normalized_total_tokens(self) -> int | None:
        if self.total_tokens is not None:
            return self.total_tokens
        if self.input_tokens is not None and self.output_tokens is not None:
            return self.input_tokens + self.output_tokens
        return None


@dataclass(frozen=True)
class GradeResult:
    grader: str
    passed: bool
    score: float
    reason: str
    failure_type: str | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)


class AgentAdapter(Protocol):
    def run(self, task: Task) -> AgentResult: ...


class RetryableAgentError(RuntimeError):
    """An adapter may raise this when a retry can safely be attempted."""


class DatasetValidationError(ValueError):
    """Raised when a task suite cannot be evaluated safely or unambiguously."""
