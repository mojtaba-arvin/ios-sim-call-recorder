#!/usr/bin/env python3
"""Dependency-free guardrails for GitHub Actions workflow definitions."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
SHA = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
ERRORS: list[str] = []

if not WORKFLOWS:
    ERRORS.append(".github/workflows: no .yml workflows found")

for path in WORKFLOWS:
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT)

    # Parse every workflow-level and job-level permissions mapping. GitHub
    # defaults are not accepted: permissions must be explicit and read-only.
    top_level_permissions_found = False
    lines = text.splitlines()
    for line_number, line in enumerate(lines):
        match = re.match(r"^( *)permissions:\\s*(.*?)\\s*$", line)
        if not match:
            continue

        indentation = len(match.group(1))
        inline_value = match.group(2)
        if indentation == 0:
            top_level_permissions_found = True

        if inline_value:
            if inline_value in {"read-all", "write-all"}:
                ERRORS.append(f"{rel}:{line_number + 1}: broad permissions are forbidden")
            else:
                ERRORS.append(
                    f"{rel}:{line_number + 1}: use an explicit permissions mapping, not inline YAML"
                )
            continue

        permission_count = 0
        child_index = line_number + 1
        while child_index < len(lines):
            child_line = lines[child_index]
            if not child_line.strip():
                child_index += 1
                continue

            child_indentation = len(child_line) - len(child_line.lstrip(" "))
            if child_indentation <= indentation:
                break

            if child_indentation == indentation + 2 and not child_line.lstrip().startswith("#"):
                permission = re.match(
                    r"^ *([A-Za-z0-9_-]+):\\s*(read|write|none)\\s*(?:#.*)?$",
                    child_line,
                )
                if permission:
                    permission_count += 1
                    if permission.group(2) == "write":
                        ERRORS.append(
                            f"{rel}:{child_index + 1}: write permission "
                            f"({permission.group(1)}) requires an explicit security exception"
                        )
                else:
                    ERRORS.append(
                        f"{rel}:{child_index + 1}: unsupported permissions entry; "
                        "use a GitHub permission set to read or none"
                    )
            child_index += 1

        if indentation == 0 and permission_count == 0:
            ERRORS.append(f"{rel}:{line_number + 1}: top-level permissions mapping is empty")

    if not top_level_permissions_found:
        ERRORS.append(f"{rel}: explicit top-level least-privilege permissions block is required")

    if re.search(r"(?m)^\s*pull_request_target\s*:", text):
        ERRORS.append(f"{rel}: pull_request_target requires a separately reviewed threat model")

    if not re.search(r"(?m)^concurrency:\s*$", text):
        ERRORS.append(f"{rel}: workflow-level concurrency group is required")

    if not re.search(r"(?m)^\s*cancel-in-progress:\s*true\s*$", text):
        ERRORS.append(f"{rel}: cancel-in-progress must be explicitly configured")

    uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", text)
    for action in uses:
        if "@" not in action:
            ERRORS.append(f"{rel}: action is not pinned to a ref: {action}")
            continue
        ref = action.rsplit("@", 1)[1]
        if not SHA.fullmatch(ref):
            ERRORS.append(f"{rel}: action must be pinned to a full 40-character SHA: {action}")

    jobs_section = text.split("jobs:", 1)[1] if "jobs:" in text else ""
    job_blocks = re.split(r"(?m)^  [A-Za-z0-9_-]+:\s*$", jobs_section)[1:]
    for index, block in enumerate(job_blocks, 1):
        if not re.search(r"(?m)^    timeout-minutes:\s*[1-9][0-9]*\s*$", block):
            ERRORS.append(f"{rel}: job block {index} is missing timeout-minutes")

if ERRORS:
    print("\n".join(f"ERROR: {item}" for item in ERRORS), file=sys.stderr)
    raise SystemExit(1)

print(f"Validated workflow guardrails in {len(WORKFLOWS)} workflow files.")
