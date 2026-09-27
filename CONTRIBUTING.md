# Contributing

Contributions should improve reproducibility, grading clarity, or safe integration boundaries.

Before opening a pull request, run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m agent_eval_lab validate evals/core_suite.json
PYTHONPATH=src python -m agent_eval_lab run --tasks evals/core_suite.json --adapter mock
```

Keep fixtures synthetic and free of secrets or customer data. Explain any changed pass/fail expectation, suite version, or regression baseline in the pull request. Do not add an LLM judge where a deterministic grader can establish the criterion.
