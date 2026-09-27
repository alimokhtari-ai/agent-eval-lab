# Changelog

## 0.2.1 — 2026-09-27

### Fixed

- corrected regression-gate semantics with explicit higher-is-better and lower-is-better directions;
- made zero-baseline gates deterministic without division-based edge cases; and
- added end-to-end CLI gate tests plus CI checks for both accepted and rejected candidates.

## 0.2.0 — 2026-09-27

### Added

- versioned 44-task synthetic core suite across tool use, schemas, permissions, retries, latency, failures, and adversarial choices;
- provider-neutral result, telemetry, grade, and failure-taxonomy contracts;
- deterministic graders for allow/deny tool policies, schemas, retries, latency, and errors;
- bounded retry execution, fault injection, JSON/HTML reports, and CI-friendly regression gates;
- standard-library HTTP adapters for OpenAI-compatible, Anthropic, and Gemini APIs; and
- safe report redaction plus stronger offline test coverage.

### Changed

- upgraded the CLI to `validate`, `run`, `benchmark`, and `compare` commands;
- made task suites explicitly named and versioned.

## 0.1.0 — 2026-09-27

- Initial offline evaluation foundation.
