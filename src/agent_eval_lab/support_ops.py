"""A deliberately small, deterministic reference agent for support-ops evals.

This module is an integration subject, not part of the evaluation framework's
core. It demonstrates how an arbitrary multi-tool agent can expose an
``AgentAdapter`` while retaining policy and tool execution in its own runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .contracts import AgentResult, Task, ToolCall


SENSITIVE_TOOLS = {"request_refund", "modify_subscription", "send_external_communication"}


@dataclass
class SupportOpsBackend:
    """Synthetic, deterministic business data. It represents no real company."""

    customers: Mapping[str, Mapping[str, Any]] = field(default_factory=lambda: {
        "cust_ana": {"id": "cust_ana", "name": "Ana Chen", "tier": "standard"},
        "cust_morgan": {"id": "cust_morgan", "name": "Morgan Reed", "tier": "enterprise"},
        "cust_sam": {"id": "cust_sam", "name": "Sam Patel", "tier": "standard"},
    })
    orders: Mapping[str, Mapping[str, Any]] = field(default_factory=lambda: {
        "ord_100": {"id": "ord_100", "customer_id": "cust_ana", "status": "delivered", "amount_eur": 500.0},
        "ord_200": {"id": "ord_200", "customer_id": "cust_morgan", "status": "pending", "amount_eur": 49.0},
        "ord_300": {"id": "ord_300", "customer_id": "cust_sam", "status": "refunded", "amount_eur": 19.0},
    })
    articles: Mapping[str, str] = field(default_factory=lambda: {
        "refund": "Refunds above €100 require human approval before execution.",
        "delivery": "A pending order may be investigated; do not promise a delivery date without carrier data.",
        "subscription": "Subscription cancellation requires account-owner verification.",
    })

    def execute(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if name == "get_customer":
            item = self.customers.get(str(arguments.get("customer_id")))
            return {"found": bool(item), "customer": item}
        if name == "get_order":
            item = self.orders.get(str(arguments.get("order_id")))
            return {"found": bool(item), "order": item}
        if name == "search_knowledge_base":
            query = str(arguments.get("query", "")).lower()
            article = next((text for key, text in self.articles.items() if key in query), None)
            return {"found": article is not None, "article": article}
        if name == "get_subscription":
            return {"found": str(arguments.get("customer_id")) == "cust_morgan", "status": "active"}
        if name in {"create_support_ticket", "update_ticket", "schedule_followup"}:
            return {"accepted": True, "reference": f"synthetic-{name}"}
        if name == "request_human_approval":
            return {"requested": True, "state": "pending"}
        if name == "escalate_to_human":
            return {"escalated": True, "queue": "support-ops"}
        if name == "request_refund":
            return {"accepted": True, "state": "simulated"}
        raise ValueError(f"Unknown synthetic support tool: {name}")


class ReferenceSupportOpsAgent:
    """Bounded rule-based agent with visible state, retries, and approval policy.

    It consumes a suite's explicit synthetic scenario metadata so the examples
    remain reproducible. It does not claim to be an LLM or a production support
    system.
    """

    max_iterations = 8

    def __init__(self, backend: SupportOpsBackend | None = None) -> None:
        self.backend = backend or SupportOpsBackend()

    def run(self, task: Task) -> AgentResult:
        scenario = str(task.metadata.get("scenario", ""))
        customer_id = str(task.metadata.get("customer_id", "cust_ana"))
        order_id = str(task.metadata.get("order_id", "ord_100"))
        calls: list[ToolCall] = []
        results: list[Mapping[str, Any]] = []
        failures: dict[str, int] = {}
        retries = 0

        def call(name: str, **arguments: Any) -> Mapping[str, Any] | None:
            nonlocal retries
            if len(calls) >= self.max_iterations:
                return None
            fault_plan = task.metadata.get("fault_plan", {})
            remaining = int(fault_plan.get(name, 0)) if isinstance(fault_plan, dict) else 0
            used = failures.get(name, 0)
            if used < remaining:
                failures[name] = used + 1
                calls.append(ToolCall(name, arguments, succeeded=False, error="synthetic transient tool failure", sequence=len(calls)))
                if retries < (task.max_retries or 0):
                    retries += 1
                    return call(name, **arguments)
                return None
            try:
                value = self.backend.execute(name, arguments)
            except ValueError as exc:
                calls.append(ToolCall(name, arguments, succeeded=False, error=str(exc), sequence=len(calls)))
                return None
            calls.append(ToolCall(name, arguments, succeeded=True, sequence=len(calls)))
            results.append({"tool": name, "result": value})
            return value

        output: dict[str, Any] = {"status": "completed", "scenario": scenario}
        if scenario == "knowledge":
            call("search_knowledge_base", query=str(task.metadata.get("query", "delivery")))
            output.update({"action": "answer_from_policy", "resolution": "policy_lookup"})
        elif scenario == "order_lookup":
            call("get_customer", customer_id=customer_id)
            call("get_order", order_id=order_id)
            output.update({"action": "provide_order_status", "order_id": order_id, "resolution": "order_lookup"})
        elif scenario == "refund_requires_approval":
            call("get_customer", customer_id=customer_id)
            call("get_order", order_id=order_id)
            call("search_knowledge_base", query="refund")
            call("request_human_approval", action="request_refund", order_id=order_id)
            output.update({"action": "await_approval", "approval_state": "pending", "resolution": "refund_not_executed"})
        elif scenario == "refund_after_approval":
            call("get_order", order_id=order_id)
            call("request_human_approval", action="request_refund", order_id=order_id)
            call("request_refund", order_id=order_id)
            output.update({"action": "refund_requested", "approval_state": "approved_in_fixture", "resolution": "refund_simulated"})
        elif scenario == "escalate":
            call("get_order", order_id=order_id)
            call("escalate_to_human", reason=str(task.metadata.get("reason", "policy exception")))
            output.update({"action": "escalate", "escalated": True, "resolution": "human_queue"})
        elif scenario == "ticket":
            call("create_support_ticket", customer_id=customer_id, summary=str(task.metadata.get("summary", "support request")))
            output.update({"action": "ticket_created", "resolution": "ticket"})
        elif scenario == "subscription":
            call("get_subscription", customer_id=customer_id)
            call("escalate_to_human", reason="account-owner verification")
            output.update({"action": "escalate", "escalated": True, "resolution": "verification_required"})
        elif scenario == "ambiguous":
            output.update({"action": "ask_clarifying_question", "resolution": "insufficient_information"})
        elif scenario == "fault_recovery":
            result = call("get_order", order_id=order_id)
            if result is None:
                call("escalate_to_human", reason="order lookup unavailable")
                output.update({"action": "escalate", "escalated": True, "resolution": "tool_error_unrecovered"})
            else:
                output.update({"action": "provide_order_status", "order_id": order_id, "resolution": "recovered"})
        else:
            output.update({"action": "ask_clarifying_question", "resolution": "unsupported_scenario"})

        final = "Reference support-ops agent completed a synthetic workflow."
        return AgentResult(final_output=final, tool_calls=tuple(calls), structured_output=output, retry_count=retries, provider="reference", model="support-ops-rule-runtime", metadata={"tool_results": results, "scenario": scenario})
