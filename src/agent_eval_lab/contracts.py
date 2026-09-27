from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Task:
    id: str
    prompt: str
    expected_tool: str
    required_output_keys: tuple[str, ...]
    max_latency_ms: float


@dataclass(frozen=True)
class AgentResult:
    tool_calls: tuple[ToolCall, ...]
    structured_output: dict[str, Any]
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    retry_count: int = 0


class AgentAdapter(Protocol):
    def run(self, task: Task) -> AgentResult: ...
