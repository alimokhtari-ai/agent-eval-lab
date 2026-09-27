"""Versioned JSON task-suite loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import DatasetValidationError, Task


@dataclass(frozen=True)
class TaskSuite:
    name: str
    version: str
    tasks: tuple[Task, ...]
    description: str = ""


_KNOWN_TYPES = {"string", "integer", "number", "boolean", "object", "array"}


def _strings(value: Any, field: str, task_id: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise DatasetValidationError(f"Task {task_id!r}: {field} must be a list of non-empty strings.")
    return tuple(value)


def task_from_mapping(item: Any) -> Task:
    if not isinstance(item, dict):
        raise DatasetValidationError("Each task must be an object.")
    task_id, input_text, category = item.get("id"), item.get("input", item.get("prompt")), item.get("category")
    if not all(isinstance(value, str) and value for value in (task_id, input_text, category)):
        raise DatasetValidationError("Each task requires non-empty id, input, and category strings.")
    expected_tool = item.get("expected_tool")
    if expected_tool is not None and (not isinstance(expected_tool, str) or not expected_tool):
        raise DatasetValidationError(f"Task {task_id!r}: expected_tool must be a non-empty string or null.")
    schema = item.get("output_schema", {})
    if not isinstance(schema, dict) or not all(isinstance(key, str) and value in _KNOWN_TYPES for key, value in schema.items()):
        raise DatasetValidationError(f"Task {task_id!r}: output_schema contains an unsupported type.")
    for field in ("max_latency_ms", "timeout_seconds"):
        value = item.get(field)
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0):
            raise DatasetValidationError(f"Task {task_id!r}: {field} must be a positive number.")
    retries = item.get("max_retries")
    if retries is not None and (not isinstance(retries, int) or isinstance(retries, bool) or retries < 0):
        raise DatasetValidationError(f"Task {task_id!r}: max_retries must be a non-negative integer.")
    metadata = item.get("metadata", {})
    if not isinstance(metadata, dict):
        raise DatasetValidationError(f"Task {task_id!r}: metadata must be an object.")
    return Task(
        id=task_id, input=input_text, category=category, expected_tool=expected_tool,
        allowed_tools=_strings(item.get("allowed_tools"), "allowed_tools", task_id),
        forbidden_tools=_strings(item.get("forbidden_tools"), "forbidden_tools", task_id),
        required_output_fields=_strings(item.get("required_output_fields", item.get("required_output_keys")), "required_output_fields", task_id),
        output_schema=schema, max_latency_ms=float(item["max_latency_ms"]) if item.get("max_latency_ms") is not None else None,
        timeout_seconds=float(item["timeout_seconds"]) if item.get("timeout_seconds") is not None else None,
        max_retries=retries, tags=_strings(item.get("tags"), "tags", task_id), metadata=metadata,
    )


def load_suite(path: Path) -> TaskSuite:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetValidationError(f"Invalid JSON in {path}: {exc.msg}.") from exc
    if isinstance(raw, list):  # Compatibility with v0.1 fixture format.
        raw = {"name": path.stem, "version": "unversioned", "tasks": raw}
    if not isinstance(raw, dict) or not isinstance(raw.get("name"), str) or not isinstance(raw.get("version"), str) or not isinstance(raw.get("tasks"), list):
        raise DatasetValidationError("A suite must contain name, version, and a tasks list.")
    tasks = tuple(task_from_mapping(item) for item in raw["tasks"])
    if not tasks:
        raise DatasetValidationError("A suite must contain at least one task.")
    ids = [task.id for task in tasks]
    duplicates = sorted({task_id for task_id in ids if ids.count(task_id) > 1})
    if duplicates:
        raise DatasetValidationError(f"Duplicate task ids: {duplicates!r}.")
    return TaskSuite(raw["name"], raw["version"], tasks, str(raw.get("description", "")))
