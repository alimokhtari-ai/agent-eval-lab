from __future__ import annotations
import unittest
from agent_eval_lab.contracts import AgentResult, Task
from agent_eval_lab.judges import JudgeGrader, JudgeVerdict

class JudgeTests(unittest.TestCase):
    def test_optional_judge_preserves_rationale_and_configuration(self) -> None:
        judge = type("Judge", (), {"judge": lambda self, task, result, rubric: JudgeVerdict(0.9, "complete", "test", "fake")})()
        grade = JudgeGrader(judge, "complete answer", 0.8).grade(Task("t", "x", "semantic"), AgentResult(final_output="x"), 1, None)
        self.assertTrue(grade.passed); self.assertEqual(grade.metadata["model"], "fake")
