#!/usr/bin/env python3
"""Dependency-free repository checks for Markdown documentation."""
from __future__ import annotations

import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\((.*?)\)")
FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(?<!`)`+[^\n`]*`+(?!`)")


def validate_docs(root: Path) -> list[str]:
    root = root.resolve()
    markdown = sorted(path for path in root.rglob("*.md") if ".git" not in path.parts)
    errors: list[str] = []

    for path in markdown:
        relative = path.relative_to(root)
        raw = path.read_text(encoding="utf-8")
        if not raw.endswith("\n"):
            errors.append(f"{relative}: missing final newline")
        if "\t" in raw:
            errors.append(f"{relative}: tab character found")

        fence_character: str | None = None
        fence_length = 0
        for number, line in enumerate(raw.splitlines(), 1):
            stripped = line.lstrip()
            fence = FENCE_RE.match(stripped)
            if fence_character is None and fence:
                marker = fence.group("fence")
                fence_character, fence_length = marker[0], len(marker)
                continue
            if fence_character is not None:
                if fence and fence.group("fence")[0] == fence_character and len(fence.group("fence")) >= fence_length:
                    fence_character = None
                    fence_length = 0
                continue

            visible_line = INLINE_CODE_RE.sub("", line)
            for raw_target in LINK_RE.findall(visible_line):
                target = raw_target.strip()
                if not target:
                    errors.append(f"{relative}:{number}: empty link target")
                    continue
                if target.startswith("<"):
                    closing = target.find(">")
                    if closing < 0:
                        errors.append(f"{relative}:{number}: malformed angle-bracket link target")
                        continue
                    target = target[1:closing]
                else:
                    target = target.split()[0]

                if not target or target.startswith(("#", "//", "http://", "https://", "mailto:", "data:")):
                    continue
                if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                    continue

                target_path = target.split("#", 1)[0].split("?", 1)[0]
                if not target_path:
                    continue
                resolved = (path.parent / target_path).resolve()
                try:
                    resolved.relative_to(root)
                except ValueError:
                    errors.append(f"{relative}:{number}: link escapes repository: {target}")
                    continue
                if not resolved.exists():
                    errors.append(f"{relative}:{number}: broken local link: {target}")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_docs(root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    count = sum(1 for path in root.rglob("*.md") if ".git" not in path.parts)
    print(f"Validated {count} Markdown files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
