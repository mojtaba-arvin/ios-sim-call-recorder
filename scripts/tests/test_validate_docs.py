from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_docs import validate_docs


class DocumentationValidatorTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_accepts_local_and_external_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "docs/target.md", "# Target\n")
            self.write(
                root,
                "README.md",
                "# Readme\n\n[Local](docs/target.md)\n\n[External](https://example.com)\n",
            )
            self.assertEqual(validate_docs(root), [])

    def test_rejects_broken_local_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "README.md", "# Readme\n\n[Missing](docs/missing.md)\n")
            errors = validate_docs(root)
            self.assertTrue(any("broken local link" in error for error in errors))

    def test_rejects_link_that_escapes_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            self.write(root, "README.md", "# Readme\n\n[Escape](../outside.md)\n")
            errors = validate_docs(root)
            self.assertTrue(any("escapes repository" in error for error in errors))

    def test_ignores_links_inside_fenced_and_inline_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(
                root,
                "README.md",
                "# Readme\n\n`[inline](missing-inline.md)`\n\n"
                "```markdown\n[block](missing-block.md)\n```\n",
            )
            self.assertEqual(validate_docs(root), [])

    def test_empty_link_target_returns_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "README.md", "# Readme\n\n[Empty]()\n")
            errors = validate_docs(root)
            self.assertTrue(any("empty link target" in error for error in errors))

    def test_reports_tabs_and_missing_final_newline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "README.md", "# Readme\n\tindented")
            errors = validate_docs(root)
            self.assertTrue(any("tab character" in error for error in errors))
            self.assertTrue(any("missing final newline" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
