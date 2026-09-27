from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import AgentResult, Task, ToolCall
from .reporting import render_terminal
from .runner import evaluate_tasks


class DeterministicMockAgent:
    """Offline adapter used to validate the harness, not to benchmark an LLM."""

    def run(self, task: Task) -> AgentResult:
        return AgentResult(
            tool_calls=(ToolCall(name=task.expected_tool, arguments={"task_id": task.id}),),
            structured_output={key: f"fixture:{key}" for key in task.required_output_keys},
        )


def load_tasks(path: Path) -> list[Task]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        Task(
            id=item["id"],
            prompt=item["prompt"],
            expected_tool=item["expected_tool"],
            required_output_keys=tuple(item["required_output_keys"]),
            max_latency_ms=float(item["max_latency_ms"]),
        )
        for item in raw
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic agent evaluation fixtures.")
    parser.add_argument("--tasks", type=Path, required=True)
    args = parser.parse_args()
    records = evaluate_tasks(DeterministicMockAgent(), load_tasks(args.tasks))
    print(render_terminal(records))
    if not all(record.passed for record in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
