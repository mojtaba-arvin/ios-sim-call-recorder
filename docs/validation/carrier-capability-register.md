# Carrier Capability Register and Forwarding Validation Plan

**Status:** execution template; no operator capability is certified by this document.  
**Related:** Issues #4, #18 and #48; `iphone-sim-compatibility-matrix.md`; `physical-device-test-protocol.md`.  
**Decision rule:** carrier forwarding, conference merge and recording are separate capabilities. A forwarding result is never promoted to a recording claim without verified two-way media.

## 1. Evidence vocabulary

Every statement must use exactly one status:

- **CONFIRMED-DOC:** current primary operator documentation explicitly describes the capability and its conditions.
- **OBSERVED:** directly observed on an identified physical SIM/device/plan tuple, with dated evidence.
- **HYPOTHESIS:** plausible but not established by documentation or a reproducible test.
- **REJECTED:** a controlled test or authoritative documentation disproves the stated capability for the exact scope.
- **UNKNOWN:** no adequate evidence exists.

A capability is scoped to country, operator, consumer/business plan, SIM/eSIM, device, carrier bundle, iOS build, network mode, roaming state and call direction. Never generalize from one plan or country to an entire carrier brand.

## 2. Operator capability register

Add one row per operator + country + plan family. Do not fill values from memory or marketing claims; link a primary source or a sanitized test record.

| Register ID | Country | Operator / MVNO | Plan family | Consumer / business | Voice network | Conference / 3-way merge | Incoming merge | Outgoing merge | Call waiting interaction | Caller-ID behavior | Conditional forwarding | Unconditional forwarding | Busy / no-answer / unreachable forwarding | Roaming behavior | Recording service/API | Evidence status | Source / test ref | Checked date | Next action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C-001 | NOT SELECTED | — | — | — | — | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | — | — | Select jurisdiction after discovery |

### Required primary-source checks

For each candidate operator, obtain the current official documentation or written operator support response for:

1. Three-way/conference calling availability and plan eligibility.
2. Whether conference calling works for incoming and outgoing initial calls.
3. Maximum participant count and whether a second call can be added while roaming.
4. Call waiting, hold/resume, VoLTE, Wi-Fi Calling and 5G voice interactions.
5. Conditional forwarding codes and supported conditions (busy, no-answer, unreachable).
6. Unconditional forwarding behavior and caller-ID preservation.
7. Whether forwarding is available while roaming and how billing is applied.
8. Any operator-provided recording service, API, notification or consent obligations.

A support-chat answer is not primary documentation unless the operator provides a dated written response with the applicable country and plan.

## 3. Forwarding is not recording

| Mechanism | What it changes | What it does not prove | Required evidence |
|---|---|---|---|
| Unconditional forwarding | Routes calls to another destination in all eligible conditions | That both parties' audio is captured or that the original handset participates | Operator behavior + two-way media test on the forwarded path |
| Busy forwarding | Routes when the line is busy under operator rules | That a conference bridge can be joined or recorded | Busy-state test + destination and caller-ID observations |
| No-answer forwarding | Routes after configured ring timeout | That the caller hears a recording notice or media is retained | Timeout behavior + consent and media test |
| Unreachable forwarding | Routes when network/device is unavailable under operator rules | That the call is recordable or the user can control the path | Airplane/off-network test + operator confirmation |
| Call waiting / add-call / merge | Adds or merges call legs on the handset/operator network | That the provider receives separate speaker channels | Physical merge test and independent channel analysis |
| Provider conference | Creates provider-owned call legs and a provider conference | That an existing native SIM call was captured | Label as app-owned provider call; test its own consent/media lifecycle |

Do not publish forwarding dial codes without validating country/operator/plan applicability. Do not send USSD/MMI commands automatically. The test operator must manually confirm the current forwarding state and rollback instructions before changing it.

## 4. Controlled forwarding test protocol

**Preconditions:** written authorization for the SIM/account; test-only numbers; consenting participants; operator instructions; known current forwarding state; no production customer calls.

For each exact tuple:

1. Record the full compatibility tuple in the iPhone/SIM matrix.
2. Capture the baseline state: call waiting, conference calling, forwarding conditions, voicemail destination and caller-ID behavior.
3. Verify each forwarding condition independently: unconditional, busy, no-answer and unreachable. Do not combine settings or assume network codes are portable.
4. For each change, record the exact operator-approved action, timestamp, confirmation response and resulting destination in a restricted evidence store. Never publish phone numbers.
5. Run one synthetic test call for the relevant condition. Record observed routing, caller-ID presentation, announcement, ring duration and failure behavior.
6. Restore the exact baseline configuration immediately after the test and verify restoration with a second test.
7. If testing a recording path, separately obtain affirmative consent from every human participant before any recording-enabled provider join. Verify local and remote speech in the resulting media; forwarding success alone is not a recording pass.
8. Keep failures, timeouts and inconclusive outcomes. Do not overwrite them with later passes.

### Test case register

| Test ID | Condition | Expected operator behavior (source-backed) | Actual route observed | Caller-ID observed | Announcement / consent | Media artifact ref | Two-way intelligibility | Rollback verified | Outcome |
|---|---|---|---|---|---|---|---|---|---|
| FWD-01 | Unconditional | UNKNOWN | NOT RUN | NOT RUN | NOT RUN | — | NOT RUN | NOT RUN | NOT RUN |
| FWD-02 | Busy | UNKNOWN | NOT RUN | NOT RUN | NOT RUN | — | NOT RUN | NOT RUN | NOT RUN |
| FWD-03 | No answer | UNKNOWN | NOT RUN | NOT RUN | NOT RUN | — | NOT RUN | NOT RUN | NOT RUN |
| FWD-04 | Unreachable | UNKNOWN | NOT RUN | NOT RUN | NOT RUN | — | NOT RUN | NOT RUN | NOT RUN |

## 5. Promotion and stop rules

- A source-backed feature may be marked CONFIRMED-DOC only for the documented country/plan scope.
- A physical capability may be marked OBSERVED only with at least three repeatable tests on the exact tuple, sanitized evidence and independent review.
- A recording pathway additionally requires intelligible local and remote speech, audio integrity inspection, participant consent evidence and retention/deletion verification.
- A positive provider-owned conference test must remain tagged APP-OWNED-PROVIDER; it cannot promote the native SIM merge pathway.
- A negative result is scoped to the tested tuple; do not infer universal failure.
- If no lawful, repeatable native-SIM route is found for the selected segment, stop the native SIM recorder proposition rather than building unsupported claims around forwarding.

## 6. Privacy and evidence handling

Public repository rows may contain only anonymized register IDs, capability status, dates, source URLs and non-identifying test summaries. Store phone numbers, account identifiers, call recordings, callback payloads and provider resource IDs only in the approved restricted evidence store. Never attach raw call media or participant details to public issues or CI artifacts.

## 7. Current disposition

No country, operator, plan or launch segment has been selected by customer evidence. Therefore C-001 and FWD-01 through FWD-04 intentionally remain UNKNOWN / NOT RUN. The next valid action is to select a jurisdiction and segment through Issue #48, then research official operator documentation and schedule authorized physical tests. This document does not certify carrier support.
