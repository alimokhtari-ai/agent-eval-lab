# Engineering Decisions

## Provider-neutral core, thin integrations

Core contracts use only the standard library. OpenAI-compatible, Anthropic, and Gemini adapters normalize HTTP responses at the edge; optional SDKs are not required just to install or test the package.

## Deterministic-first grading

Tool policy, contracts, retries, and latency are objectively testable and remain code-based. This gives useful failure reasons, avoids spend, and keeps CI reproducible.

## Offline-first CI

CI validates a 44-task deterministic suite, reports, package build, and tests without credentials or paid calls. Hosted adapters fail with a clear missing-credential message and are not invoked by CI.

## Static reports

JSON is the portable evidence format; static HTML is deliberately dependency-light, escaped, and reviewable. It is not a dashboard product.

## Cost handling

The system records adapter-reported tokens and cost but does not hard-code volatile pricing. Exact cost requires an adapter/provider source or a clearly versioned external pricing policy.

## Direction-aware regression gates

Relative regression is not symmetric: a lower success rate is harmful, while higher latency is harmful. Policies therefore declare direction and accept only per-task metrics with a defined interpretation. Absolute ceilings remain available for safety invariants such as zero forbidden actions. Ambiguous rules are configuration errors, not silently guessed behavior.
