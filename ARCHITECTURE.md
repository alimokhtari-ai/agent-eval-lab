# Architecture

Agent Eval Lab keeps the boundary between an agent and its evaluation stable.

```mermaid
sequenceDiagram
  participant S as TaskSuite
  participant A as AgentAdapter
  participant R as Runtime
  participant G as Deterministic graders
  participant P as Report + policy
  S->>R: validated Task
  R->>A: run(task)
  A-->>R: normalized AgentResult
  R->>G: result, duration, error
  G-->>R: GradeResult[]
  R->>P: EvaluationRecord[]
```

## Domain model

- `Task` is immutable, versioned through its suite, and declares only observable expectations: expected/allowed/forbidden tools, output fields/types, budgets, tags, and non-sensitive metadata.
- `AgentResult` normalizes text, tool calls, structured output, retries, token/cost telemetry, provider/model identifiers, and errors. Telemetry is optional.
- `GradeResult` is inspectable: grader name, score, reason, metadata, and failure taxonomy.
- `EvaluationRecord` combines the task, measured duration, grades, attempts, and visible error.

## Boundaries

The runner owns timing, bounded retries for `RetryableAgentError`, and failure capture. Graders are small deterministic objects; new graders can implement `grade(task, result, duration_ms, error)`. Reporters consume records and do not invoke agents. Provider adapters live in `adapters.py`; they return common contracts and do not leak HTTP or SDK types into the core.

The design intentionally does not supply a universal agent runtime, parallel scheduler, database, or tracing backend. Those are deployment choices. A domain agent only needs the minimal `run(task) -> AgentResult` protocol.
