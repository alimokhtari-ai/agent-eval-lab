# Security Policy

## Sensitive evaluation data

Evaluation traces can contain prompts, tool arguments, model output, customer information, or credentials. Keep fixtures synthetic by default. Do not commit customer data, API keys, bearer tokens, passwords, authorization headers, or production traces.

Credentials are read only from environment variables by hosted adapters. They are never accepted as CLI flags or written by the package. Reports redact common secret-bearing keys including `authorization`, `api_key`, `token`, `password`, and `secret`; review output before sharing because redaction is not a data-classification system.

## Reporting vulnerabilities

Do not open a public issue for a vulnerability. Use GitHub private vulnerability reporting or email [thisaimentor10@gmail.com](mailto:thisaimentor10@gmail.com) with subject `Security report: Agent Eval Lab`. Exclude credentials and private traces from the initial report.
