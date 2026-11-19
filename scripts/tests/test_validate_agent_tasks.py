from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_agent_tasks import validate_state_transition, validate_task_graph


def make_task(task_id: str, dependencies: list[str] | None = None) -> dict:
    return {
        "id": task_id,
        "title": "Atomic example",
        "outcome": "A measurable result",
        "status": "queued",
        "dependencies": dependencies or [],
        "owner": None,
        "role": "implementer",
        "scope": {
            "in_scope": ["src/example.swift"],
            "out_of_scope": ["backend"],
            "owned_paths": ["src/example.swift"],
        },
        "acceptance_criteria": ["Failure behavior is covered by a regression test"],
        "risk": "medium",
        "required_evidence_tier": "unit",
        "validation": {"commands": ["swift test"], "scenarios": ["failure"]},
        "rollback": "Revert the task-scoped commit",
        "evidence": {
            "exact_head_sha": None,
            "tests_status": "not-run",
            "independent_review": False,
            "documentation_updated": False,
        },
    }


class AgentTaskValidatorTests(unittest.TestCase):
    def test_state_machine_accepts_documented_transitions(self) -> None:
        for current, target in (
            ("queued", "running"),
            ("queued", "blocked"),
            ("running", "review"),
            ("running", "failed"),
            ("blocked", "queued"),
            ("review", "done"),
            ("review", "running"),
        ):
            with self.subTest(current=current, target=target):
                self.assertTrue(validate_state_transition(current, target))

    def test_state_machine_rejects_reopening_done_tasks(self) -> None:
        with self.assertRaisesRegex(ValueError, "not allowed"):
            validate_state_transition("done", "running")

    def test_resetting_running_or_failed_tasks_requires_reason(self) -> None:
        for current in ("running", "failed"):
            with self.subTest(current=current):
                with self.assertRaisesRegex(ValueError, "reset_reason"):
                    validate_state_transition(current, "queued")
                with self.assertRaisesRegex(ValueError, "reset_reason"):
                    validate_state_transition(current, "queued", reset_reason=[])
                self.assertTrue(validate_state_transition(
                    current, "queued", reset_reason="Reassign after worker timeout"
                ))

    def test_accepts_acyclic_task_graph(self) -> None:
        first = make_task("IOS-1")
        second = make_task("IOS-2", ["IOS-1"])
        self.assertEqual(validate_task_graph([first, second]), [])

    def test_rejects_unknown_dependency(self) -> None:
        task = make_task("IOS-1", ["MISSING"])
        errors = validate_task_graph([task])
        self.assertTrue(any("unknown dependency" in error for error in errors))

    def test_rejects_dependency_cycle(self) -> None:
        first = make_task("IOS-1", ["IOS-2"])
        second = make_task("IOS-2", ["IOS-1"])
        errors = validate_task_graph([first, second])
        self.assertTrue(any("dependency cycle" in error for error in errors))

    def test_rejects_duplicate_task_ids(self) -> None:
        errors = validate_task_graph([make_task("IOS-1"), make_task("IOS-1")])
        self.assertTrue(any("duplicate task id" in error for error in errors))

    def test_done_requires_exact_sha_successful_tests_review_and_docs(self) -> None:
        task = make_task("IOS-1")
        task["status"] = "done"
        errors = validate_task_graph([task])
        self.assertTrue(any("exact_head_sha" in error for error in errors))
        self.assertTrue(any("successful exact-head tests" in error for error in errors))
        self.assertTrue(any("independent review" in error for error in errors))
        self.assertTrue(any("reviewer identity" in error for error in errors))
        self.assertTrue(any("Actions run URL" in error for error in errors))
        self.assertTrue(any("documentation status" in error for error in errors))

        task["evidence"] = {
            "exact_head_sha": "a" * 40,
            "tests_status": "success",
            "ci_run_url": "https://github.com/example/repo/actions/runs/123",
            "independent_review": True,
            "reviewer": "independent-reviewer",
            "documentation_updated": True,
        }
        self.assertEqual(validate_task_graph([task]), [])

    def test_done_task_requires_all_dependencies_to_be_done(self) -> None:
        prerequisite = make_task("IOS-1")
        dependent = make_task("IOS-2", ["IOS-1"])
        dependent["status"] = "done"
        dependent["evidence"] = {
            "exact_head_sha": "a" * 40,
            "tests_status": "success",
            "independent_review": True,
            "documentation_updated": True,
        }
        errors = validate_task_graph([prerequisite, dependent])
        self.assertTrue(any("dependency 'IOS-1' is not done" in error for error in errors))

        prerequisite["status"] = "done"
        prerequisite["evidence"] = copy.deepcopy(dependent["evidence"])
        self.assertEqual(validate_task_graph([prerequisite, dependent]), [])

    def test_blocked_task_requires_a_blocker(self) -> None:
        task = make_task("IOS-1")
        task["status"] = "blocked"
        errors = validate_task_graph([task])
        self.assertTrue(any("require a blocker" in error for error in errors))

    def test_malformed_classification_types_return_errors_not_exceptions(self) -> None:
        task = make_task("IOS-1")
        task["status"] = ["done"]
        task["risk"] = []
        task["required_evidence_tier"] = {}
        errors = validate_task_graph([task])
        self.assertTrue(any("invalid status" in error for error in errors))
        self.assertTrue(any("invalid risk" in error for error in errors))
        self.assertTrue(any("invalid evidence tier" in error for error in errors))

    def test_rejects_missing_observable_acceptance_criteria(self) -> None:
        task = make_task("IOS-1")
        task["acceptance_criteria"] = []
        errors = validate_task_graph([task])
        self.assertTrue(any("acceptance_criteria" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
