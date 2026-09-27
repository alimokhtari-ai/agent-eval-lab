from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_eval_lab.contracts import AgentResult, Task, ToolCall
from agent_eval_lab.dataset import load_suite
from agent_eval_lab.graders import ApprovalGrader, TrajectoryGrader
from agent_eval_lab.reporting import build_report, summary, write_html_report
from agent_eval_lab.runner import evaluate_task, evaluate_tasks
from agent_eval_lab.support_ops import ReferenceSupportOpsAgent


ROOT = Path(__file__).resolve().parents[1]


class SupportOpsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = load_suite(ROOT / "evals" / "support_ops_v1.json")

    def test_domain_suite_is_versioned_and_substantial(self) -> None:
        self.assertEqual(self.suite.name, "support-operations")
        self.assertGreaterEqual(len(self.suite.tasks), 75)
        self.assertTrue(any(task.requires_approval for task in self.suite.tasks))
        self.assertTrue(any(task.requires_escalation for task in self.suite.tasks))

    def test_reference_agent_completes_the_full_synthetic_suite(self) -> None:
        records = evaluate_tasks(ReferenceSupportOpsAgent(), list(self.suite.tasks))
        self.assertTrue(all(record.passed for record in records))
        self.assertEqual(len(records), 75)

    def test_approval_grader_rejects_a_premature_refund(self) -> None:
        task = Task("approval", "refund", "human_approval", requires_approval=True)
        result = AgentResult(tool_calls=(ToolCall("request_refund", sequence=0), ToolCall("request_human_approval", sequence=1)))
        grade = ApprovalGrader().grade(task, result, 0, None)
        self.assertFalse(grade.passed)
        self.assertEqual(grade.failure_type, "forbidden_action")

    def test_trajectory_accepts_a_valid_subsequence_not_only_exact_trace(self) -> None:
        task = Task("trajectory", "x", "workflow", expected_tool_sequence=("get_customer", "get_order"))
        result = AgentResult(tool_calls=(ToolCall("get_customer", sequence=0), ToolCall("search_knowledge_base", sequence=1), ToolCall("get_order", sequence=2)))
        self.assertTrue(TrajectoryGrader().grade(task, result, 0, None).passed)

    def test_reference_agent_retries_a_transient_tool_failure(self) -> None:
        task = next(item for item in self.suite.tasks if item.id == "recovery-01")
        record = evaluate_task(ReferenceSupportOpsAgent(), task)
        self.assertTrue(record.passed)
        self.assertEqual(record.result.retry_count if record.result else None, 1)
        self.assertEqual([call.succeeded for call in record.result.tool_calls] if record.result else [], [False, True])

    def test_domain_summary_exposes_observable_controls(self) -> None:
        records = evaluate_tasks(ReferenceSupportOpsAgent(), list(self.suite.tasks))
        data = summary(records)
        self.assertEqual(data["approval_compliance"], 1.0)
        self.assertEqual(data["escalation_accuracy"], 1.0)
        self.assertEqual(data["unnecessary_tool_rate"], 0.0)
        self.assertIn("human_approval", data["category_success_rates"])

    def test_report_redacts_nested_sensitive_trace_data_and_renders_trajectory(self) -> None:
        task = Task("secret", "x", "workflow", metadata={"trace": {"password": "not-for-report"}})
        agent = type("Agent", (), {"run": lambda self, _: AgentResult(tool_calls=(ToolCall("get_order"),), metadata={"deep": [{"client_secret": "not-for-report"}]})})()
        record = evaluate_task(agent, task)
        self.assertNotIn("not-for-report", str(build_report([record])))
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.html"
            write_html_report(target, [record])
            self.assertIn("get_order", target.read_text(encoding="utf-8"))
