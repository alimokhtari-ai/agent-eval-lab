from __future__ import annotations
import os
import unittest
from agent_eval_lab.adapters import CredentialUnavailable, ModelConfig, OpenAICompatibleAdapter, adapter_from_config
from agent_eval_lab.contracts import Task

class AdapterTests(unittest.TestCase):
    def test_mock_config_needs_no_credentials(self) -> None:
        result = adapter_from_config(ModelConfig("mock", "deterministic-v1")).run(Task("t", "x", "schema", required_output_fields=("id",), output_schema={"id":"string"}))
        self.assertEqual(result.provider, "mock")
    def test_missing_openai_key_fails_without_network(self) -> None:
        prior = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with self.assertRaises(CredentialUnavailable): OpenAICompatibleAdapter(ModelConfig("openai-compatible", "x")).run(Task("t", "x", "schema"))
        finally:
            if prior is not None: os.environ["OPENAI_API_KEY"] = prior

    def test_reference_support_adapter_needs_no_credentials(self) -> None:
        adapter = adapter_from_config(ModelConfig("reference-support", "synthetic"))
        result = adapter.run(Task("support", "help", "ambiguity", max_tool_calls=0, metadata={"scenario": "ambiguous"}))
        self.assertEqual(result.provider, "reference")
