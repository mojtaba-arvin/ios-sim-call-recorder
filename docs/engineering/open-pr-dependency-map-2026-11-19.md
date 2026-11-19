# Open pull-request dependency map

**Snapshot:** 2026-11-19  
**Repository:** `mojtaba-arvin/ios-sim-call-recorder`  
**Scope:** open PRs at the snapshot time. Refresh this document before changing branch bases, rebasing, or merging.

## Dependency graph

```text
main
├── #1  docs/recording-pathways-research
├── #35 docs/product-readme-and-status
├── #39 research/conference-bridge-provider-evaluation
├── #7  feat/swift-recording-core-foundation
│   └── #19 feat/iphone-capture-pathway-discovery
│       ├── #21 feat/recording-import-validation
│       │   └── #23 feat/ios-app-import-shell
│       │       └── #24 feat/ios-share-export-playback-lifecycle
│       │           └── #25 feat/ios-recording-retention-catalog-recovery-v2
│       │               └── #26 feat/ios-storage-integration-tests
│       │                   └── #27 feat/ios-playback-controls-interruption-handling
│       │                       ├── #31 feat/ios-library-accessibility-states
│       │                       ├── #32 fix/ios-import-full-decode-validation
│       │                       └── #38 fix/ios-pending-playback-request-invalidation
│       ├── #29 test/audio-quality-analysis-tooling
│       ├── #30 feat/recording-session-cancellation
│       │   └── #34 fix/core-adapter-failure-cleanup
│       └── #37 feat/accessory-compatibility-assessment
├── #9  chore/agent-git-engineering-governance
│   └── #28 chore/agent-rd-skills-and-templates
└── #11 feat/conference-bridge-backend-core
    └── #13 feat/twilio-webhook-signature-adapter
        └── #15 feat/postgres-transactional-outbox
            └── #17 feat/provider-command-dispatcher-core
                └── #36 fix/backend-dispatcher-validate-command-inputs
```

PR #1 and #35 are independent research/product documentation baselines. PR #7, #9 and #11 are independent main-based foundations. The iOS/app stack is serial because later changes build on prior storage, UI and CI behavior. PRs #29 and #30 are independent side branches from #19; PR #28 extends the governance branch from #9.

## Snapshot heads and bases

| PR | Head branch | Head SHA | Base branch | Dependency |
|---:|---|---|---|---|
| #1 | `docs/recording-pathways-research` | `bb50671edc4301a6605bcc2baa06c709e5c8dec3` | `main` | Independent |
| #7 | `feat/swift-recording-core-foundation` | `8aa1fed83e1baa5484a91ae6727a6e54a58abaf9` | `main` | Independent |
| #9 | `chore/agent-git-engineering-governance` | `b26e5240ba9c20a863b9d06019db220984757913` | `main` | Independent |
| #11 | `feat/conference-bridge-backend-core` | `ea1de3054afaf63930a9a623894e555dfd0412f4` | `main` | Independent |
| #13 | `feat/twilio-webhook-signature-adapter` | `8b9297a27c0b0a4e575a2e56910f9ef61e37133c` | #11 | Backend stack |
| #15 | `feat/postgres-transactional-outbox` | `ab22b8d79086cbb7e2ffb91f9a871dec024e42a6` | #13 | Backend stack |
| #17 | `feat/provider-command-dispatcher-core` | `b33c60680c8814e3b23b02b2ee4ef24bfab06247` | #15 | Backend stack |
| #19 | `feat/iphone-capture-pathway-discovery` | `430ea6647ba04786e36df1ce57b683cfc30632dd` | #7 | iOS stack |
| #21 | `feat/recording-import-validation` | `215a3bf314c0c55291b94dbc850c240ec416877e` | #19 | iOS stack |
| #23 | `feat/ios-app-import-shell` | `e8370f033ad8b303b2724601c242d436c269578a` | #21 | iOS stack |
| #24 | `feat/ios-share-export-playback-lifecycle` | `39d724920deba51c14acbd5ec78992eb74c0c92b` | #23 | iOS stack |
| #25 | `feat/ios-recording-retention-catalog-recovery-v2` | `871162e3b4799590054b87305aef57671827a8fd` | #24 | iOS stack |
| #26 | `feat/ios-storage-integration-tests` | `cabda934c1f2e593d5efaae7934bcf30b12f2235` | #25 | iOS stack |
| #27 | `feat/ios-playback-controls-interruption-handling` | `9517157e3dc48813ecede33a87d3c1d88105bf62` | #26 | iOS stack |
| #31 | `feat/ios-library-accessibility-states` | `95b95fd5748ea75fd40fb46f1effc0a46bc067cc` | #27 | iOS stack |
| #32 | `fix/ios-import-full-decode-validation` | `ac345260f794e30dff030d11802eca41d4bdaee8` | #27 | iOS import validation |
| #34 | `fix/core-adapter-failure-cleanup` | `21d9e8895a10537c643d94ae8e4a1890780514c2` | #30 | Core lifecycle cleanup |
| #35 | `docs/product-readme-and-status` | `6bfd6c5c22c93934f411720ca599cd94b72effcf` | `main` | Independent product/release documentation |
| #39 | `research/conference-bridge-provider-evaluation` | `1b530ee5965bc95a4a4d757e91035dd6609fcfc4` | `main` | Provider-neutral bridge contract and evaluation proposal |
| #36 | `fix/backend-dispatcher-validate-command-inputs` | `7107b72ccf4cf108ba14aa739790c9565ffebce4` | #17 | Backend command validation |
| #37 | `feat/accessory-compatibility-assessment` | `131474f9b4aaa8f142133eaee484d58e077e3bd3` | #19 | Accessory compatibility/evidence gate |
| #38 | `fix/ios-pending-playback-request-invalidation` | `8952c356e8fed25704d2aef65ec935a5c7751e77` | #27 | Playback lifecycle race fix |
| #28 | `chore/agent-rd-skills-and-templates` | `e447fa74d4fcab3352bcb08b372eb069b4fe0663` | #9 | Governance stack (latest synchronized head) |
| #29 | `test/audio-quality-analysis-tooling` | `3992ab85f0156c380ceabf07ed50f5fb534f7397` | #19 | iOS test tooling |
| #30 | `feat/recording-session-cancellation` | `b9bc82363910a17d226b05a1aa5719ea6d80afd3` | #19 | Core lifecycle |

## Integration order

1. Review and integrate independent foundations only after their own CI/review gates: #1, #7, #9, #11 and #35. PR #39 is a separate documentation proposal and should be reviewed against the backend implementation before merge.
2. Integrate governance extension #28 after #9.
3. Integrate backend stack in order #13 → #15 → #17 → #36 after #11.
4. Integrate the iOS core/capture stack #19 after #7. PR #29 and #30 can then be reviewed independently against #19.
5. Integrate app/storage stack strictly in order #21 → #23 → #24 → #25 → #26 → #27, then review #31 (accessibility), #32 (audio-payload validation) and #38 (pending playback lookup invalidation) as separate PRs. PR #34 depends on #30 and adds failure-path adapter cleanup.
6. Review #37 after #19; it adds accessory connector/route compatibility and strict physical-evidence promotion gates.
7. Resolve Issue #18 and Issue #20 physical-device gates before enabling provider recording or advertising accessory compatibility.

## Operational rules

- The branch name alone is not proof that a PR is current; refresh head/base SHAs before every write.
- A PR base must be its immediate prerequisite branch. Do not retarget a stacked PR to main merely to make it mergeable.
- A successful check applies only to the exact head SHA that ran it.
- Use file-path filters rather than enumerating stacked base branches. Each workflow should run only when its owned source/test paths change, regardless of the PR's target branch; policy CI owns workflow-file changes. Keep manual dispatch for deliberate full runs.
- Keep all PRs unmerged until independent review and exact-head required checks are complete. No direct main commits, auto-merge or force-push.
- Physical-device and carrier tests cannot be substituted with CI, unit tests or Simulator runs.


## 2026-11-19 execution refresh

- PR #37 is stacked on #19 and adds accessory connector/route compatibility plus strict physical evidence promotion. Its exact-head Swift run #44511799963 passed 67 package tests (0 failures) on head `131474f9b4aaa8f142133eaee484d58e077e3bd3`.
- PR #38 is stacked on #27 and prevents stale asynchronous playback lookups from reopening deleted/expired recordings. Exact-head Swift run #44511369730 passed; iOS Simulator app-hosted run #44511369716 passed 13 tests (0 failures) on head `8952c356e8fed25704d2aef65ec935a5c7751e77`.
- Neither PR is merged. PR #37 has no physical-device evidence; PR #38 validates local playback lifecycle only.
- This map refresh is being committed on the #28 governance branch; refresh its own head SHA after this commit and rerun the repository policy workflow.


## CI and branch hygiene refresh (2026-11-19)

- PR #9 now centralizes four path-scoped workflows: Swift/audio analyzer checks, backend tests, iOS Simulator build and repository policy validation. The Swift workflow covers `Packages/CallRecorderCore/**` and the WAV analyzer source/tests; backend CI covers `backend/**`; macOS build covers app sources, package dependencies and `project.yml`; policy CI covers workflows, validators, agent instructions and tests.
- Swift core and WAV analyzer checks are separate workflows, so a change in one no longer starts the other.
- Backend dependency installation now uses the setup-python pip cache keyed by `backend/requirements.txt`; the previous `--no-cache-dir` flag was removed because it bypassed that cache.
- Each expensive source workflow has a lightweight Ubuntu change-detection job that diffs the PR merge ref against its exact base SHA. This is required because newly introduced workflow files were observed to start even when their source-path filters did not match. The detector gates the Swift, analyzer, backend and macOS build jobs; `workflow_dispatch` deliberately bypasses the gate.
- The macOS build avoids installing XcodeGen when it is already present and uses quiet xcodebuild output. On the observed macOS 15 runner XcodeGen was not preinstalled, so the install step still runs there.
- Exact-head repository-policy run #44517272385 passed on PR #9 SHA `b26e5240ba9c20a863b9d06019db220984757913`. It validated the workflow guardrails and validator tests.
- Exact-head repository-policy run #44517418342 passed on PR #28 SHA `e447fa74d4fcab3352bcb08b372eb069b4fe0663`; workflow guardrails, all agent-asset/task validators and their regression tests passed.
- The earlier workflow-addition runs #44515146779 (iOS) and #44515131676 (Backend) failed before build/test execution because PR #9's base did not yet contain `project.yml` or `backend/requirements.txt`. They are completed failures, not queued runs. The new preflight gate prevents this false-positive work.
- PR #39 converts the previously untracked research branch into a draft documentation PR; its contract is proposal-only and does not prove provider or carrier compatibility.
- Branch audit found 27 branches total: 25 are heads of open PRs, one is `main`, and `feat/ios-recording-retention-catalog-recovery` is the only branch not referenced by an open PR. Its head is `06b4ada8fb3120e9ffd11f6a500635f110afff12`; it has six commits not present in the v2 branch's ancestry, so the earlier claim that it had no commits ahead of `main` was incorrect. The retention policy source is identical in both branches; the v2 implementation adds a regular-file check during orphan cleanup, propagates refresh failures in the UI and updates the architecture documentation. The old branch's behavior is superseded by active PR #25, so deletion is reasonable after preserving the head SHA above. The connected GitHub actions do not expose delete-ref; repository owner must run the supplied `gh api -X DELETE ...` command.
