# Security Policy

## Sensitive evaluation data

Evaluation traces can contain prompts, tool arguments, model output, customer information, or credentials. Keep fixtures synthetic by default. Do not commit customer data, API keys, bearer tokens, passwords, authorization headers, or production traces.

Credentials are read only from environment variables by hosted adapters. They are never accepted as CLI flags or written by the package. Reports redact common secret-bearing keys including `authorization`, `api_key`, `client_secret`, `token`, `password`, and `secret`; review output before sharing because redaction is not a data-classification system. Provider HTTP errors are reduced to a status-class message rather than copying an error body into reports, since provider responses can echo sensitive request context.

## Synthetic Support Operations fixtures

The Support Operations reference agent uses invented names, IDs, amounts, and policy text solely to exercise agent behavior. It must not be repointed at customer systems or populated with production traces without a separate data-handling review. Tool arguments and results can still be sensitive in a real integration; use least-privilege credentials and retain only the minimum trace data needed for evaluation.

## Reporting vulnerabilities

Do not open a public issue for a vulnerability. Use GitHub private vulnerability reporting or email [thisaimentor10@gmail.com](mailto:thisaimentor10@gmail.com) with subject `Security report: Agent Eval Lab`. Exclude credentials and private traces from the initial report.
