from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from agent_eval_lab.contracts import DatasetValidationError
from agent_eval_lab.dataset import load_suite

class DatasetTests(unittest.TestCase):
    def _write(self, data: object) -> Path:
        target = Path(tempfile.mkdtemp()) / "suite.json"; target.write_text(json.dumps(data)); return target
    def test_duplicate_ids_fail(self) -> None:
        with self.assertRaises(DatasetValidationError): load_suite(self._write({"name":"x","version":"1","tasks":[{"id":"a","input":"x","category":"c"},{"id":"a","input":"x","category":"c"}]}))
    def test_invalid_schema_type_fails(self) -> None:
        with self.assertRaises(DatasetValidationError): load_suite(self._write({"name":"x","version":"1","tasks":[{"id":"a","input":"x","category":"c","output_schema":{"x":"date"}}]}))
    def test_core_suite_is_versioned_and_substantial(self) -> None:
        suite = load_suite(Path("evals/core_suite.json")); self.assertEqual(suite.version, "1.0"); self.assertGreaterEqual(len(suite.tasks), 40)
