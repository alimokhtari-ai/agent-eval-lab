"""Minimal custom-agent integration; no provider SDK is required by the core."""

from agent_eval_lab.contracts import AgentResult, Task, ToolCall


class MyAgent:
    def run(self, task: Task) -> AgentResult:
        # Replace this deterministic behavior with an adapter to your application.
        output = {field: f"example:{field}" for field in task.required_output_fields}
        calls = () if task.expected_tool is None else (ToolCall(task.expected_tool, {"task_id": task.id}),)
        return AgentResult(final_output="example", tool_calls=calls, structured_output=output, provider="my-agent", model="my-model")
