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

    if not re.search(r"(?m)^permissions:\s*$", text):
        ERRORS.append(f"{rel}: explicit least-privilege permissions block is required")

    if re.search(r"(?m)^\s*permissions:\s*(?:write-all|read-all)", text):
        ERRORS.append(f"{rel}: broad permissions are forbidden")

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

    job_blocks = re.split(r"(?m)^  [A-Za-z0-9_-]+:\s*$", text)[1:]
    for index, block in enumerate(job_blocks, 1):
        if not re.search(r"(?m)^    timeout-minutes:\s*[1-9][0-9]*\s*$", block):
            ERRORS.append(f"{rel}: job block {index} is missing timeout-minutes")

if ERRORS:
    print("\n".join(f"ERROR: {item}" for item in ERRORS), file=sys.stderr)
    raise SystemExit(1)

print(f"Validated workflow guardrails in {len(WORKFLOWS)} workflow files.")
