# R&D task contract and lifecycle

The machine-readable task contract in `.agents/templates/task.example.json` is the execution record for atomic repository work. The Markdown template remains useful for planning and human-readable context; the JSON contract is the source for dependency and completion validation.

## States

| State | Meaning | Required information |
|---|---|---|
| queued | Ready but not assigned | Outcome, scope, dependencies, acceptance criteria |
| running | Actively being implemented | Owner and role |
| blocked | Cannot proceed without a named prerequisite | Blocker and dependency |
| review | Implementation published for review | Owner, role and PR URL |
| done | All completion gates satisfied | Exact 40-character head SHA, successful tests, independent review and documentation status |
| failed | Attempt ended unsuccessfully | Failure reason and retained evidence |

## Transition rules

- queued → running or blocked
- running → blocked, review, failed or queued (only after an explicit reset)
- blocked → queued or running once the blocker is resolved
- review → done, running (changes requested) or failed
- failed → queued only after recording the corrective action
- done is terminal; follow-up work receives a new task ID

The validator checks status-specific fields, unique IDs, dependency existence and cycles. Its `validate_state_transition(current, target, reset_reason=...)` function enforces the documented state machine and requires a corrective reason when resetting a running or failed task. It does not execute work, authenticate a reviewer or verify a GitHub run itself; those remain orchestrator/CI responsibilities.

## Atomicity and ownership

- One task has one accountable implementer and an independently assigned reviewer for review-gated work.
- Owned paths must be explicit. Parallel tasks may not own overlapping files unless an interface contract and coordination plan are recorded.
- Dependencies must point to existing task IDs and form an acyclic graph.
- Each task has observable acceptance criteria, a risk class, required evidence tier and rollback plan.
- A task cannot be marked done merely because a PR exists or a build succeeded.

## Validation

Run:

```sh
python3 scripts/validate_agent_tasks.py .agents/templates/task.example.json
python3 -m unittest discover -s scripts/tests -p 'test_validate_agent_tasks.py'
```

A successful validator run proves only that the task records satisfy the structural contract. Exact-head CI, independent review and any required physical-device/carrier evidence must still be verified separately.
