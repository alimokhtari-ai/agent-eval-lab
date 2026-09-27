"""Optional semantic judging extension point; never part of default grading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import AgentResult, GradeResult, Task


@dataclass(frozen=True)
class JudgeVerdict:
    score: float
    rationale: str
    provider: str
    model: str


class SemanticJudge(Protocol):
    def judge(self, task: Task, result: AgentResult, rubric: str) -> JudgeVerdict: ...


class JudgeGrader:
    """Wrap a supplied judge with explicit rubric and threshold metadata."""
    name = "semantic_judge"
    def __init__(self, judge: SemanticJudge, rubric: str, threshold: float = 0.8) -> None:
        self.judge, self.rubric, self.threshold = judge, rubric, threshold
    def grade(self, task: Task, result: AgentResult, duration_ms: float, error: str | None) -> GradeResult:
        if error:
            return GradeResult(self.name, False, 0.0, "Judge skipped because execution failed.", "judge_failure")
        verdict = self.judge.judge(task, result, self.rubric)
        passed = verdict.score >= self.threshold
        return GradeResult(self.name, passed, verdict.score, verdict.rationale, None if passed else "task_failure", {"provider": verdict.provider, "model": verdict.model, "threshold": self.threshold, "rubric": self.rubric})
