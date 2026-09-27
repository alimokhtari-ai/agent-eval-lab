from __future__ import annotations

import unittest

from agent_eval_lab.contracts import AgentResult, Task, ToolCall
from agent_eval_lab.runner import evaluate_task


TASK = Task("t1", "test", "lookup", ("id",), 1000)


class PassingAgent:
    def run(self, task: Task) -> AgentResult:
        return AgentResult((ToolCall("lookup"),), {"id": "1"})


class BrokenAgent:
    def run(self, task: Task) -> AgentResult:
        raise RuntimeError("adapter unavailable")


class EvaluationRunnerTests(unittest.TestCase):
    def test_passing_result_passes_all_graders(self) -> None:
        record = evaluate_task(PassingAgent(), TASK)
        self.assertTrue(record.passed)
        self.assertIsNone(record.error)

    def test_adapter_exception_is_visible_failure(self) -> None:
        record = evaluate_task(BrokenAgent(), TASK)
        self.assertFalse(record.passed)
        self.assertIn("adapter unavailable", record.error or "")

    def test_missing_contract_key_fails_without_exception(self) -> None:
        class IncompleteAgent:
            def run(self, task: Task) -> AgentResult:
                return AgentResult((ToolCall("lookup"),), {})

        record = evaluate_task(IncompleteAgent(), TASK)
        self.assertFalse(record.contract_passed)
        self.assertFalse(record.passed)
