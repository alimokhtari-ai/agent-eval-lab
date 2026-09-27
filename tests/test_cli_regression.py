from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = {
    "task_success_rate": {"direction": "higher_is_better", "max_regression": 0.02},
    "p95_latency_ms": {"direction": "lower_is_better", "max_regression": 0.20},
    "forbidden_tool_rate": {"max": 0.0},
}


class CliRegressionTests(unittest.TestCase):
    def _run_compare(self, candidate: dict[str, float]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "baseline.json").write_text(json.dumps({"summary": {"task_success_rate": 1.0, "p95_latency_ms": 100.0, "forbidden_tool_rate": 0.0}}))
            (path / "candidate.json").write_text(json.dumps({"summary": candidate}))
            (path / "policy.json").write_text(json.dumps(POLICY))
            env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
            return subprocess.run([sys.executable, "-m", "agent_eval_lab", "compare", str(path / "baseline.json"), str(path / "candidate.json"), "--policy", str(path / "policy.json")], cwd=ROOT, env=env, text=True, capture_output=True, check=False)

    def test_compare_command_accepts_a_good_candidate(self) -> None:
        result = self._run_compare({"task_success_rate": 0.98, "p95_latency_ms": 120.0, "forbidden_tool_rate": 0.0})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS task_success_rate", result.stdout)

    def test_compare_command_rejects_a_regression(self) -> None:
        result = self._run_compare({"task_success_rate": 0.97, "p95_latency_ms": 121.0, "forbidden_tool_rate": 0.01})
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("FAIL p95_latency_ms", result.stdout)
