from __future__ import annotations
import unittest
from agent_eval_lab.contracts import AgentResult, Task, ToolCall
from agent_eval_lab.graders import AllowedToolGrader, ForbiddenToolGrader, LatencyBudgetGrader, StructuredOutputGrader, ToolSelectionGrader

class GraderTests(unittest.TestCase):
    def test_no_tool_task_rejects_side_effect(self) -> None:
        grade = ToolSelectionGrader().grade(Task("t", "x", "safety"), AgentResult(tool_calls=(ToolCall("send_email"),)), 1, None)
        self.assertEqual(grade.failure_type, "unexpected_tool")
    def test_allow_list_rejects_unlisted_tool(self) -> None:
        grade = AllowedToolGrader().grade(Task("t", "x", "tool", allowed_tools=("search_docs",)), AgentResult(tool_calls=(ToolCall("send_email"),)), 1, None)
        self.assertEqual(grade.failure_type, "forbidden_tool")
    def test_forbidden_list_rejects_prohibited_tool(self) -> None:
        grade = ForbiddenToolGrader().grade(Task("t", "x", "tool", forbidden_tools=("delete_customer",)), AgentResult(tool_calls=(ToolCall("delete_customer"),)), 1, None)
        self.assertFalse(grade.passed)
    def test_integer_schema_does_not_accept_boolean(self) -> None:
        grade = StructuredOutputGrader().grade(Task("t", "x", "schema", output_schema={"count":"integer"}), AgentResult(structured_output={"count":True}), 1, None)
        self.assertEqual(grade.failure_type, "schema_violation")
    def test_latency_budget_rejects_slow_run(self) -> None:
        grade = LatencyBudgetGrader().grade(Task("t", "x", "latency", max_latency_ms=5), AgentResult(), 6, None)
        self.assertEqual(grade.failure_type, "timeout")
