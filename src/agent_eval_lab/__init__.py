"""Provider-neutral, deterministic-first evaluation primitives for AI agents."""

__version__ = "0.2.0"

from .contracts import AgentResult, GradeResult, Task, ToolCall
from .runner import EvaluationRecord, evaluate_tasks

__all__ = ["AgentResult", "EvaluationRecord", "GradeResult", "Task", "ToolCall", "evaluate_tasks"]
