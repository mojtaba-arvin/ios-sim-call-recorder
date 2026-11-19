#!/usr/bin/env python3
"""Validate R&D task contracts and their dependency graph using only the stdlib."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

STATUSES = {"queued", "running", "blocked", "review", "done", "failed"}
RISKS = {"low", "medium", "high", "critical"}
EVIDENCE_TIERS = {"static", "unit", "integration", "simulator", "physical-device", "carrier"}
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
REQUIRED = {
    "id", "title", "outcome", "status", "dependencies", "owner", "role",
    "scope", "acceptance_criteria", "risk", "required_evidence_tier",
    "validation", "evidence", "rollback",
}
ALLOWED_TRANSITIONS = {
    "queued": {"running", "blocked"},
    "running": {"blocked", "review", "failed", "queued"},
    "blocked": {"queued", "running"},
    "review": {"done", "running", "failed"},
    "failed": {"queued"},
    "done": set(),
}


def validate_state_transition(current: str, target: str, *, reset_reason: str | None = None) -> bool:
    if (
        not isinstance(current, str) or current not in STATUSES
        or not isinstance(target, str) or target not in STATUSES
    ):
        raise ValueError("current and target must be known task states")
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"task state transition '{current}' -> '{target}' is not allowed")
    if target == "queued" and current in {"running", "failed"} and not (
        isinstance(reset_reason, str) and reset_reason.strip()
    ):
        raise ValueError("resetting a running or failed task requires a corrective reset_reason")
    return True


def validate_task_graph(tasks: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}

    for index, task in enumerate(tasks):
        prefix = f"task[{index}]"
        if not isinstance(task, dict):
            errors.append(f"{prefix}: expected an object")
            continue
        missing = sorted(REQUIRED - task.keys())
        errors.extend(f"{prefix}: missing field '{field}'" for field in missing)
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append(f"{prefix}: id must be a non-empty string")
            continue
        if task_id in by_id:
            errors.append(f"duplicate task id: {task_id}")
        else:
            by_id[task_id] = task

    for task_id, task in by_id.items():
        status = task.get("status")
        status_valid = isinstance(status, str) and status in STATUSES
        if not status_valid:
            errors.append(f"{task_id}: invalid status '{status}'")
        risk = task.get("risk")
        if not isinstance(risk, str) or risk not in RISKS:
            errors.append(f"{task_id}: invalid risk classification")
        evidence_tier = task.get("required_evidence_tier")
        if not isinstance(evidence_tier, str) or evidence_tier not in EVIDENCE_TIERS:
            errors.append(f"{task_id}: invalid evidence tier")

        dependencies = task.get("dependencies")
        if not isinstance(dependencies, list) or any(not isinstance(dep, str) for dep in dependencies):
            errors.append(f"{task_id}: dependencies must be a list of task IDs")
            dependencies = []
        for dependency in dependencies:
            if dependency not in by_id:
                errors.append(f"{task_id}: unknown dependency '{dependency}'")

        scope = task.get("scope")
        if not isinstance(scope, dict):
            errors.append(f"{task_id}: scope must be an object")
        else:
            for field in ("in_scope", "out_of_scope", "owned_paths"):
                value = scope.get(field)
                if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
                    errors.append(f"{task_id}: scope.{field} must be a list of non-empty strings")

        criteria = task.get("acceptance_criteria")
        if not isinstance(criteria, list) or not criteria or any(not isinstance(item, str) or not item.strip() for item in criteria):
            errors.append(f"{task_id}: acceptance_criteria must contain observable criteria")

        if status_valid and status in {"running", "review"} and not task.get("owner"):
            errors.append(f"{task_id}: {status} tasks require an owner")
        if status_valid and status in {"running", "review"} and not task.get("role"):
            errors.append(f"{task_id}: {status} tasks require an assigned role")
        if status_valid and status == "blocked" and not task.get("blocker"):
            errors.append(f"{task_id}: blocked tasks require a blocker")
        if status_valid and status == "failed" and not task.get("failure_reason"):
            errors.append(f"{task_id}: failed tasks require a failure_reason")
        if status_valid and status == "review" and not task.get("pull_request_url"):
            errors.append(f"{task_id}: review tasks require a pull_request_url")

        if status_valid and status == "done":
            for dependency in dependencies:
                prerequisite = by_id.get(dependency)
                if prerequisite is not None and prerequisite.get("status") != "done":
                    errors.append(f"{task_id}: dependency '{dependency}' is not done")
            evidence = task.get("evidence")
            if not isinstance(evidence, dict):
                errors.append(f"{task_id}: done tasks require an evidence object")
                continue
            sha = evidence.get("exact_head_sha")
            if not isinstance(sha, str) or not SHA_PATTERN.fullmatch(sha):
                errors.append(f"{task_id}: done tasks require a 40-character exact_head_sha")
            if evidence.get("tests_status") != "success":
                errors.append(f"{task_id}: done tasks require successful exact-head tests")
            if evidence.get("independent_review") is not True:
                errors.append(f"{task_id}: done tasks require independent review")
            if evidence.get("documentation_updated") is not True:
                errors.append(f"{task_id}: done tasks require documentation status")

    # Detect dependency cycles without relying on input order.
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited or task_id not in by_id:
            return
        if task_id in visiting:
            errors.append(f"dependency cycle includes task '{task_id}'")
            return
        visiting.add(task_id)
        dependencies = by_id[task_id].get("dependencies", [])
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if isinstance(dependency, str):
                    visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in by_id:
        visit(task_id)

    return errors


def load_task_files(paths: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    tasks: list[dict[str, Any]] = []
    errors: list[str] = []
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.json")))
        else:
            files.append(path)
    for path in files:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{path}: cannot load JSON ({error})")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path}: task document must contain one JSON object")
            continue
        tasks.append(value)
    return tasks, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="task JSON files or directories")
    args = parser.parse_args()
    tasks, errors = load_task_files(args.paths)
    errors.extend(validate_task_graph(tasks))
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"Validated {len(tasks)} R&D task contract(s) and dependency graph.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
