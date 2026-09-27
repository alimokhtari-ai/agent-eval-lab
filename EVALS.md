# Evaluation Methodology

## Task format

Each task names the expected tool, required structured-output keys, and a latency budget. Fixtures should represent an observable workflow rather than a vague prompt-quality preference.

## Scoring

Each task receives three deterministic checks:

1. **Tool selection** — did the agent call the expected tool?
2. **Output contract** — does the structured output include every required key?
3. **Latency** — did the task finish within its stated budget?

A task passes only when all three checks pass and the adapter did not raise an exception.

## Reproducibility

The included mock adapter is deterministic and runs without network access or credentials. It validates the harness itself. Real adapters should record model identifier, configuration, task fixture revision, and any measured token or cost telemetry.

## Limitations

- This repository does not claim real-world LLM quality or benchmark rankings.
- A passing contract does not prove an answer is factually correct.
- Latency results are meaningful only in the deployment environment where they are measured.
- Sensitive production prompts and customer data should never be committed as fixtures.
