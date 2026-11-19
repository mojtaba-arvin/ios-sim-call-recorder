# Open pull-request dependency map

**Snapshot:** 2026-11-19  
**Repository:** `mojtaba-arvin/ios-sim-call-recorder`  
**Scope:** open PRs at the snapshot time. Refresh this document before changing branch bases, rebasing, or merging.

## Dependency graph

```text
main
├── #1  docs/recording-pathways-research
├── #7  feat/swift-recording-core-foundation
│   └── #19 feat/iphone-capture-pathway-discovery
│       ├── #21 feat/recording-import-validation
│       │   └── #23 feat/ios-app-import-shell
│       │       └── #24 feat/ios-share-export-playback-lifecycle
│       │           └── #25 feat/ios-recording-retention-catalog-recovery-v2
│       │               └── #26 feat/ios-storage-integration-tests
│       │                   └── #27 feat/ios-playback-controls-interruption-handling
│       │                       ├── #31 feat/ios-library-accessibility-states
│                       └── #32 fix/ios-import-full-decode-validation
│       ├── #29 test/audio-quality-analysis-tooling
│       └── #30 feat/recording-session-cancellation
├── #9  chore/agent-git-engineering-governance
│   └── #28 chore/agent-rd-skills-and-templates
└── #11 feat/conference-bridge-backend-core
    └── #13 feat/twilio-webhook-signature-adapter
        └── #15 feat/postgres-transactional-outbox
            └── #17 feat/provider-command-dispatcher-core
```

PR #1 is an independent research baseline. PR #7, #9 and #11 are independent main-based foundations. The iOS/app stack is serial because later changes build on prior storage, UI and CI behavior. PRs #29 and #30 are independent side branches from #19; PR #28 extends the governance branch from #9.

## Snapshot heads and bases

| PR | Head branch | Head SHA | Base branch | Dependency |
|---:|---|---|---|---|
| #1 | `docs/recording-pathways-research` | `bb50671edc4301a6605bcc2baa06c709e5c8dec3` | `main` | Independent |
| #7 | `feat/swift-recording-core-foundation` | `8aa1fed83e1baa5484a91ae6727a6e54a58abaf9` | `main` | Independent |
| #9 | `chore/agent-git-engineering-governance` | `5975ce5ecfc2bc3475edf14dcb1f170df0fe8164` | `main` | Independent |
| #11 | `feat/conference-bridge-backend-core` | `ea1de3054afaf63930a9a623894e555dfd0412f4` | `main` | Independent |
| #13 | `feat/twilio-webhook-signature-adapter` | `8b9297a27c0b0a4e575a2e56910f9ef61e37133c` | #11 | Backend stack |
| #15 | `feat/postgres-transactional-outbox` | `ab22b8d79086cbb7e2ffb91f9a871dec024e42a6` | #13 | Backend stack |
| #17 | `feat/provider-command-dispatcher-core` | `a1c630de8226948ae353af4de53aab422eec0e12` | #15 | Backend stack |
| #19 | `feat/iphone-capture-pathway-discovery` | `430ea6647ba04786e36df1ce57b683cfc30632dd` | #7 | iOS stack |
| #21 | `feat/recording-import-validation` | `215a3bf314c0c55291b94dbc850c240ec416877e` | #19 | iOS stack |
| #23 | `feat/ios-app-import-shell` | `e8370f033ad8b303b2724601c242d436c269578a` | #21 | iOS stack |
| #24 | `feat/ios-share-export-playback-lifecycle` | `39d724920deba51c14acbd5ec78992eb74c0c92b` | #23 | iOS stack |
| #25 | `feat/ios-recording-retention-catalog-recovery-v2` | `871162e3b4799590054b87305aef57671827a8fd` | #24 | iOS stack |
| #26 | `feat/ios-storage-integration-tests` | `cabda934c1f2e593d5efaae7934bcf30b12f2235` | #25 | iOS stack |
| #27 | `feat/ios-playback-controls-interruption-handling` | `9517157e3dc48813ecede33a87d3c1d88105bf62` | #26 | iOS stack |
| #31 | `feat/ios-library-accessibility-states` | `95b95fd5748ea75fd40fb46f1effc0a46bc067cc` | #27 | iOS stack |
| #32 | `fix/ios-import-full-decode-validation` | `019789cc7644bd540c49065c2c2133927aaed1b0` | #27 | iOS import validation |
| #28 | `chore/agent-rd-skills-and-templates` | `17583c0db879028cc09f52a3a3f9f8192f19d0c9` | #9 | Governance stack |
| #29 | `test/audio-quality-analysis-tooling` | `f67d27df1ced580202da90fcf3fb57dc920cae22` | #19 | iOS test tooling |
| #30 | `feat/recording-session-cancellation` | `c399f35f6c416a5957e6f39d7191367e772c03d7` | #19 | Core lifecycle |

## Integration order

1. Review and integrate independent foundations only after their own CI/review gates: #1, #7, #9 and #11.
2. Integrate governance extension #28 after #9.
3. Integrate backend stack in order #13 → #15 → #17 after #11.
4. Integrate the iOS core/capture stack #19 after #7. PR #29 and #30 can then be reviewed independently against #19.
5. Integrate app/storage stack strictly in order #21 → #23 → #24 → #25 → #26 → #27 → #31.
6. Resolve Issue #18 and Issue #20 physical-device gates before enabling provider recording or advertising accessory compatibility.

## Operational rules

- The branch name alone is not proof that a PR is current; refresh head/base SHAs before every write.
- A PR base must be its immediate prerequisite branch. Do not retarget a stacked PR to main merely to make it mergeable.
- A successful check applies only to the exact head SHA that ran it.
- If a workflow's `pull_request.branches` filter omits a stacked PR's base branch, the check may never run. Add the base branch to the workflow in the prerequisite branch and verify a new run.
- Keep all PRs unmerged until independent review and exact-head required checks are complete. No direct main commits, auto-merge or force-push.
- Physical-device and carrier tests cannot be substituted with CI, unit tests or Simulator runs.
