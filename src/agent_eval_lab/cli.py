"""Intentional standard-library CLI for validation, runs, reports, and gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .adapters import ModelConfig, adapter_from_config
from .contracts import DatasetValidationError
from .dataset import load_suite
from .regression import DEFAULT_POLICY, compare_reports
from .reporting import render_terminal, write_html_report, write_json_report
from .runner import evaluate_tasks


def _config_from_args(args: argparse.Namespace) -> ModelConfig:
    if args.config:
        raw = json.loads(args.config.read_text(encoding="utf-8"))
        adapter = raw.get("adapter", raw)
        return ModelConfig(provider=adapter.get("provider", "mock"), model=adapter.get("model", "deterministic-v1"), temperature=float(adapter.get("temperature", 0)), max_tokens=adapter.get("max_tokens"), timeout_seconds=float(adapter.get("timeout_seconds", 30)), retries=int(adapter.get("retries", 0)), endpoint=adapter.get("endpoint"))
    return ModelConfig(provider=args.adapter, model=args.model or "deterministic-v1", timeout_seconds=args.timeout, retries=args.retries, endpoint=args.endpoint)


def _run(args: argparse.Namespace) -> int:
    suite = load_suite(args.tasks)
    records = evaluate_tasks(adapter_from_config(_config_from_args(args)), list(suite.tasks))
    print(render_terminal(records))
    if args.json_out: write_json_report(args.json_out, records, suite)
    if args.html_out: write_html_report(args.html_out, records, suite)
    return 0 if all(record.passed for record in records) else 1


def _validate(args: argparse.Namespace) -> int:
    suite = load_suite(args.tasks)
    print(f"Valid: {suite.name} v{suite.version} ({len(suite.tasks)} tasks)")
    return 0


def _compare(args: argparse.Namespace) -> int:
    baseline, candidate = json.loads(args.baseline.read_text()), json.loads(args.candidate.read_text())
    policy: dict[str, dict[str, float]] = json.loads(args.policy.read_text()) if args.policy else DEFAULT_POLICY
    gates = compare_reports(baseline, candidate, policy)
    for gate in gates:
        print(f"{'PASS' if gate.passed else 'FAIL'} {gate.metric}: {gate.baseline} -> {gate.candidate}. {gate.reason}")
    return 0 if all(gate.passed for gate in gates) else 1


def _benchmark(args: argparse.Namespace) -> int:
    exit_code = 0
    for config in args.config:
        name = config.stem
        print(f"\n== {name} ==")
        run_args = argparse.Namespace(tasks=args.tasks, config=config, adapter="mock", model=None, timeout=30, retries=0, endpoint=None, json_out=args.output_dir / f"{name}.json" if args.output_dir else None, html_out=args.output_dir / f"{name}.html" if args.output_dir else None)
        exit_code = max(exit_code, _run(run_args))
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-eval", description="Provider-neutral evaluation for AI agent behavior.")
    commands = parser.add_subparsers(dest="command", required=True)
    def run_options(target: argparse.ArgumentParser) -> None:
        target.add_argument("--tasks", type=Path, required=True, help="Versioned JSON task suite")
        target.add_argument("--adapter", choices=("mock", "reference-support", "openai-compatible", "anthropic", "gemini"), default="mock")
        target.add_argument("--model"); target.add_argument("--endpoint"); target.add_argument("--timeout", type=float, default=30); target.add_argument("--retries", type=int, default=0)
        target.add_argument("--config", type=Path, help="JSON adapter configuration")
        target.add_argument("--json-out", type=Path); target.add_argument("--html-out", type=Path)
    run = commands.add_parser("run", help="Run a suite against one adapter"); run_options(run); run.set_defaults(handler=_run)
    validate = commands.add_parser("validate", help="Validate a task suite"); validate.add_argument("tasks", type=Path); validate.set_defaults(handler=_validate)
    compare = commands.add_parser("compare", help="Apply regression gates to reports"); compare.add_argument("baseline", type=Path); compare.add_argument("candidate", type=Path); compare.add_argument("--policy", type=Path); compare.set_defaults(handler=_compare)
    benchmark = commands.add_parser("benchmark", help="Run a suite for each JSON adapter config"); benchmark.add_argument("--tasks", type=Path, required=True); benchmark.add_argument("--config", type=Path, action="append", required=True); benchmark.add_argument("--output-dir", type=Path); benchmark.set_defaults(handler=_benchmark)
    return parser


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0].startswith("--"): argv.insert(0, "run")  # v0.1 compatibility
    try:
        args = build_parser().parse_args(argv)
        raise SystemExit(args.handler(args))
    except (DatasetValidationError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"agent-eval: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__": main()
