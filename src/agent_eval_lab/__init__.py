"""Offline-first deterministic evaluation primitives for AI agents."""

from .contracts import AgentResult, Task, ToolCall
from .runner import evaluate_tasks

__all__ = ["AgentResult", "Task", "ToolCall", "evaluate_tasks"]
