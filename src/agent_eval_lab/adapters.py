"""Provider-neutral adapters plus optional HTTP integrations with no SDK dependency.

The hosted adapters are intentionally thin examples. Production agents should
usually expose their own domain-specific AgentAdapter rather than forcing their
runtime into a generic prompt wrapper.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import AgentResult, RetryableAgentError, Task, ToolCall


class CredentialUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str
    temperature: float = 0.0
    max_tokens: int | None = None
    timeout_seconds: float = 30.0
    retries: int = 0
    endpoint: str | None = None


class DeterministicMockAgent:
    """A conformant offline adapter used to test the platform, never an LLM claim."""
    def run(self, task: Task) -> AgentResult:
        output: dict[str, Any] = {}
        for field in set(task.required_output_fields) | set(task.output_schema):
            kind = task.output_schema.get(field, "string")
            output[field] = {"integer": 1, "number": 1.0, "boolean": True, "object": {}, "array": []}.get(kind, f"fixture:{field}")
        calls = () if task.expected_tool is None else (ToolCall(task.expected_tool, {"task_id": task.id}, succeeded=True, sequence=0),)
        return AgentResult(final_output="deterministic fixture", tool_calls=calls, structured_output=output, provider="mock", model="deterministic-v1")


class FaultInjectingAdapter:
    """Deterministic fault wrapper for recovery and reporting tests."""
    def __init__(self, wrapped: Any, mode: str, failures_before_success: int = 0) -> None:
        self.wrapped, self.mode, self.failures_before_success, self.calls = wrapped, mode, failures_before_success, 0

    def run(self, task: Task) -> AgentResult:
        self.calls += 1
        if self.mode == "transient" and self.calls <= self.failures_before_success:
            raise RetryableAgentError("injected transient failure")
        if self.mode == "provider_error":
            raise RuntimeError("injected provider failure")
        result = self.wrapped.run(task)
        if self.mode == "forbidden_tool":
            return AgentResult(**{**result.__dict__, "tool_calls": result.tool_calls + (ToolCall("send_email", {}),)})
        if self.mode == "malformed_output":
            return AgentResult(**{**result.__dict__, "structured_output": {}})
        return result


class _HttpAdapter:
    key_environment: str = ""
    provider: str = ""
    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    def _key(self) -> str:
        value = os.environ.get(self.key_environment)
        if not value:
            raise CredentialUnavailable(f"{self.key_environment} is required for the {self.provider} adapter.")
        return value

    def _post(self, url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers}, method="POST")
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:  # nosec B310: endpoint is explicit user config
                return json.loads(response.read().decode())
        except HTTPError as exc:
            body = exc.read().decode(errors="replace")[:500]
            if exc.code in {408, 429, 500, 502, 503, 504}:
                raise RetryableAgentError(f"HTTP {exc.code}: {body}") from exc
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise RetryableAgentError(f"network error: {exc.reason}") from exc


def _parse_json_output(text: str | None) -> tuple[str | None, dict[str, Any] | None]:
    if not text:
        return text, None
    try:
        parsed = json.loads(text)
        return text, parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return text, None


class OpenAICompatibleAdapter(_HttpAdapter):
    key_environment, provider = "OPENAI_API_KEY", "openai-compatible"
    def run(self, task: Task) -> AgentResult:
        endpoint = self.config.endpoint or "https://api.openai.com/v1/chat/completions"
        tools = [{"type": "function", "function": {"name": tool, "description": "Evaluation tool"}} for tool in task.allowed_tools]
        payload: dict[str, Any] = {"model": self.config.model, "temperature": self.config.temperature, "messages": [{"role": "user", "content": task.input}]}
        if self.config.max_tokens is not None: payload["max_tokens"] = self.config.max_tokens
        if tools: payload["tools"] = tools
        data = self._post(endpoint, {"Authorization": f"Bearer {self._key()}"}, payload)
        message, usage = data["choices"][0]["message"], data.get("usage", {})
        calls = tuple(ToolCall(call["function"]["name"], _json_object(call["function"].get("arguments")), sequence=index) for index, call in enumerate(message.get("tool_calls", [])))
        text, structured = _parse_json_output(message.get("content"))
        return AgentResult(text, calls, structured, usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("total_tokens"), provider=self.provider, model=data.get("model", self.config.model))


class AnthropicAdapter(_HttpAdapter):
    key_environment, provider = "ANTHROPIC_API_KEY", "anthropic"
    def run(self, task: Task) -> AgentResult:
        endpoint = self.config.endpoint or "https://api.anthropic.com/v1/messages"
        payload: dict[str, Any] = {"model": self.config.model, "max_tokens": self.config.max_tokens or 1024, "messages": [{"role": "user", "content": task.input}]}
        if task.allowed_tools: payload["tools"] = [{"name": tool, "description": "Evaluation tool", "input_schema": {"type": "object", "properties": {}}} for tool in task.allowed_tools]
        data = self._post(endpoint, {"x-api-key": self._key(), "anthropic-version": "2023-06-01"}, payload)
        blocks, usage = data.get("content", []), data.get("usage", {})
        text = "\n".join(block.get("text", "") for block in blocks if block.get("type") == "text") or None
        calls = tuple(ToolCall(block["name"], block.get("input", {}), sequence=index) for index, block in enumerate(blocks) if block.get("type") == "tool_use")
        final, structured = _parse_json_output(text)
        return AgentResult(final, calls, structured, usage.get("input_tokens"), usage.get("output_tokens"), provider=self.provider, model=self.config.model)


class GeminiAdapter(_HttpAdapter):
    key_environment, provider = "GEMINI_API_KEY", "gemini"
    def run(self, task: Task) -> AgentResult:
        endpoint = self.config.endpoint or f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.model}:generateContent?key={self._key()}"
        declarations = [{"name": tool, "description": "Evaluation tool", "parameters": {"type": "OBJECT", "properties": {}}} for tool in task.allowed_tools]
        payload: dict[str, Any] = {"contents": [{"parts": [{"text": task.input}]}]}
        if declarations: payload["tools"] = [{"functionDeclarations": declarations}]
        data = self._post(endpoint, {}, payload)
        parts, usage = data["candidates"][0]["content"].get("parts", []), data.get("usageMetadata", {})
        text = "\n".join(part.get("text", "") for part in parts if "text" in part) or None
        calls = tuple(ToolCall(part["functionCall"]["name"], part["functionCall"].get("args", {}), sequence=index) for index, part in enumerate(parts) if "functionCall" in part)
        final, structured = _parse_json_output(text)
        return AgentResult(final, calls, structured, usage.get("promptTokenCount"), usage.get("candidatesTokenCount"), usage.get("totalTokenCount"), provider=self.provider, model=self.config.model)


def _json_object(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def adapter_from_config(config: ModelConfig) -> Any:
    providers = {"mock": DeterministicMockAgent, "openai-compatible": OpenAICompatibleAdapter, "anthropic": AnthropicAdapter, "gemini": GeminiAdapter}
    try:
        return providers[config.provider](config) if config.provider != "mock" else DeterministicMockAgent()
    except KeyError as exc:
        raise ValueError(f"Unknown adapter provider {config.provider!r}.") from exc
