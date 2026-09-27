# Evaluation Methodology

## Suite design

`evals/core_suite.json` is `core-agent-behavior` v1.0: 44 synthetic, reviewable tasks covering tool selection, output schemas, retry budgets, permission boundaries, failure handling, latency, ambiguous requests, and adversarial tool selection. Synthetic data makes offline CI safe; it is not a substitute for a domain suite built from reviewed production failure modes.

Suites are JSON objects with `name`, `version`, and `tasks`. Validation rejects malformed JSON, duplicate ids, missing core fields, invalid type names, invalid budgets, and malformed tool lists. A task expresses observable expectations, not vague response preference.

## Grading

Default graders are deterministic:

- expected tool selection;
- allowed and forbidden tool policy;
- required output fields and basic type contracts;
- latency and retry budgets; and
- visible error behavior.

A task passes only when every applicable grade passes. The report preserves each individual reason; aggregate rates never replace failure evidence.

## Metrics

Implemented aggregates are task success, tool accuracy, forbidden-tool rate, schema validity, average/p50/p95/fastest/slowest latency, retry rate, failure distribution, and reported token/cost totals. Missing cost or token telemetry is `N/A`. P95 is omitted below 20 tasks because it is not meaningful enough at that sample size.

## Judges

LLM-as-judge belongs only where a criterion cannot be checked objectively, such as semantic completeness. It is not bundled as a default grader. A future judge integration must record provider, model, rubric, rationale, threshold, and repeat-run methodology; judges can exhibit self-preference, prompt sensitivity, stochasticity, and model correlation. They are evidence, not ground truth.

## Reproducibility and interpretation

Reports record timestamp, package version, git commit when available, suite metadata, runtime environment, task-level grades, and safe adapter telemetry. Do not compare tiny runs as provider rankings. Any real comparison must state the suite, configuration, date, model, sample size, and limitations narrowly.

## Regression policy semantics

Regression gates operate on report summaries. Relative gates require an explicit direction and are restricted to stable per-task metrics: `task_success_rate`, `tool_accuracy`, and `structured_output_validity` are `higher_is_better`; `forbidden_tool_rate`, latency metrics, `retry_rate`, and `average_cost_per_task_usd` are `lower_is_better`. A `max` rule expresses an absolute ceiling, which is useful for a zero-tolerance safety rate. The implementation evaluates against the tolerated boundary instead of dividing by the baseline, so zero baselines remain meaningful. Counts and totals are intentionally not eligible for relative gates because task count and telemetry availability change their interpretation.
