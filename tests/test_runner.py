from __future__ import annotations
import unittest
from agent_eval_lab.adapters import DeterministicMockAgent, FaultInjectingAdapter
from agent_eval_lab.contracts import AgentResult, Task
from agent_eval_lab.runner import evaluate_task

TASK = Task("t1", "test", "tool-selection", "lookup", ("lookup",), (), ("id",), {"id": "string"}, 1000, max_retries=1)

class RunnerTests(unittest.TestCase):
    def test_conformant_result_passes_all_graders(self) -> None:
        self.assertTrue(evaluate_task(DeterministicMockAgent(), TASK).passed)
    def test_adapter_exception_is_visible_failure(self) -> None:
        class Broken:
            def run(self, task: Task) -> AgentResult: raise RuntimeError("adapter unavailable")
        record = evaluate_task(Broken(), TASK)
        self.assertIn("provider_error", record.failure_types)
    def test_forbidden_tool_is_categorized(self) -> None:
        task = Task(**{**TASK.__dict__, "forbidden_tools": ("send_email",)})
        self.assertIn("forbidden_tool", evaluate_task(FaultInjectingAdapter(DeterministicMockAgent(), "forbidden_tool"), task).failure_types)
    def test_transient_failure_recovers_inside_budget(self) -> None:
        record = evaluate_task(FaultInjectingAdapter(DeterministicMockAgent(), "transient", 1), TASK)
        self.assertTrue(record.passed); self.assertEqual(record.result.retry_count, 1)
    def test_retry_exhaustion_is_visible(self) -> None:
        record = evaluate_task(FaultInjectingAdapter(DeterministicMockAgent(), "transient", 2), TASK)
        self.assertIn("retry_exhausted", record.error or "")
