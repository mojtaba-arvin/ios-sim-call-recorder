#!/usr/bin/env python3
"""Small dependency-free repository checks for Markdown documentation."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN = sorted(p for p in ROOT.rglob("*.md") if ".git" not in p.parts)
LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
errors: list[str] = []

for path in MARKDOWN:
    rel = path.relative_to(ROOT)
    raw = path.read_text(encoding="utf-8")
    if not raw.endswith("\n"):
        errors.append(f"{rel}: missing final newline")
    if "\t" in raw:
        errors.append(f"{rel}: tab character found")

    in_fence = False
    for number, line in enumerate(raw.splitlines(), 1):
        if line.lstrip().startswith("```") or line.lstrip().startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in LINK_RE.findall(line):
            target = target.strip().split()[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            target_path = target.split("#", 1)[0].split("?", 1)[0]
            if not target_path:
                continue
            resolved = (path.parent / target_path).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"{rel}:{number}: link escapes repository: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{rel}:{number}: broken local link: {target}")

if errors:
    print("\n".join(errors), file=sys.stderr)
    raise SystemExit(1)

print(f"Validated {len(MARKDOWN)} Markdown files.")
