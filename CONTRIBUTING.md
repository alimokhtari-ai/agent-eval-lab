# Contributing

Contributions should improve reproducibility, grading clarity, or safe integration boundaries.

Before opening a pull request, run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m agent_eval_lab --tasks evals/tasks/tool_use.json
```

Keep fixtures synthetic and free of secrets or customer data. Explain any changed pass/fail expectation in the pull request.
