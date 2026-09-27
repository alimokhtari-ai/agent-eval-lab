from __future__ import annotations

import unittest

from agent_eval_lab.contracts import AgentResult, Task, ToolCall
from agent_eval_lab.reporting import summary
from agent_eval_lab.runner import evaluate_task


class ReportingTests(unittest.TestCase):
    def test_summary_does_not_invent_cost_when_adapter_does_not_supply_it(self) -> None:
        task = Task("t", "p", "tool", ("id",), 1000)

        class Agent:
            def run(self, _: Task) -> AgentResult:
                return AgentResult((ToolCall("tool"),), {"id": "1"})

        data = summary([evaluate_task(Agent(), task)])
        self.assertFalse(data["cost_telemetry_available"])
        self.assertIsNone(data["total_estimated_cost_usd"])
