from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from agent_eval_lab.contracts import AgentResult, Task
from agent_eval_lab.reporting import build_report, summary, write_html_report
from agent_eval_lab.runner import evaluate_task

class ReportingTests(unittest.TestCase):
    def test_summary_does_not_invent_cost(self) -> None:
        task = Task("t", "p", "schema", None, (), (), ("id",), {"id": "string"})
        record = evaluate_task(type("Agent", (), {"run": lambda self, _: AgentResult(structured_output={"id": "1"})})(), task)
        self.assertIsNone(summary([record])["total_estimated_cost_usd"])
    def test_report_redacts_common_secret_fields(self) -> None:
        task = Task("t", "p", "schema", None, (), (), ("id",), {"id": "string"}, metadata={"api_key": "do-not-print"})
        record = evaluate_task(type("Agent", (), {"run": lambda self, _: AgentResult(structured_output={"id": "1"}, metadata={"token": "do-not-print"})})(), task)
        encoded = str(build_report([record])); self.assertNotIn("do-not-print", encoded); self.assertIn("[REDACTED]", encoded)
    def test_html_escapes_task_content(self) -> None:
        task = Task("<script>", "p", "schema", None, (), (), ("id",), {"id": "string"})
        record = evaluate_task(type("Agent", (), {"run": lambda self, _: AgentResult(structured_output={"id": "1"})})(), task)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.html"; write_html_report(target, [record]); self.assertIn("&lt;script&gt;", target.read_text())
