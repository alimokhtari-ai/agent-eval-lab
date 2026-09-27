# Engineering Decisions

## Deterministic graders before LLM judges

The first checks are exact and explainable: expected tool, required fields, and latency budget. LLM-as-a-judge can be useful later, but it adds cost and nondeterminism and should not replace basic contract validation.

## Adapter boundary instead of a bundled model SDK

The core intentionally contains no API client and no credentials. This keeps local evaluation safe, avoids vendor lock-in, and makes adapters responsible for model-specific telemetry.

## JSON fixtures in version control

Small, reviewed JSON fixtures make regression changes visible in pull requests. Large, private, or customer-derived datasets belong in a controlled data system, not this repository.
