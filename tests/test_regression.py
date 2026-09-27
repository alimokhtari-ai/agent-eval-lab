from __future__ import annotations
import unittest
from agent_eval_lab.regression import compare_reports

class RegressionTests(unittest.TestCase):
    def test_policy_passes_at_threshold(self) -> None:
        results = compare_reports({"summary":{"task_success_rate":1.0,"forbidden_tool_rate":0.0}}, {"summary":{"task_success_rate":0.98,"forbidden_tool_rate":0.0}}); self.assertTrue(all(result.passed for result in results))
    def test_policy_fails_on_forbidden_call(self) -> None:
        results = compare_reports({"summary":{"task_success_rate":1.0,"forbidden_tool_rate":0.0}}, {"summary":{"task_success_rate":1.0,"forbidden_tool_rate":0.1}}); self.assertFalse(next(result for result in results if result.metric == "forbidden_tool_rate").passed)
