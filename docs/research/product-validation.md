# Product validation: evidence, assumptions, and go/no-go plan

**Snapshot:** 2026-11-20  
**Status:** desk research complete for the current repository evidence; customer demand, willingness to pay, and physical capture feasibility are **not validated**.  
**Decision owner:** product owner  
**Purpose:** determine whether this should be a native-SIM recording product, a companion/archive product, an accessory-led product, or a separate app-owned VoIP product before spending on a production backend or hardware.

> This is a decision document, not a claim of product-market fit. No customer interviews, paid pilots, carrier commitments, physical-device call tests, legal opinions, or production economics were available for this review. Unknowns remain unknown.

## 1. Executive decision

**Do not market or build this as a universal iPhone SIM-call recorder.** Public iOS APIs do not give an ordinary third-party app access to Phone.app's private live cellular-call audio. Apple's own call recording is unavailable in a number of regions, including the EU, Iran and Oman, but that restriction does not create a third-party capture entitlement.

The repository already has a useful companion foundation: user-mediated audio import, private storage, catalog, playback, export, retention and recovery. That is technically credible as a companion/archive workflow, but it is not yet differentiated enough to establish a standalone paid product.

The conference-bridge route is plausible only on specific carrier/device/plan combinations. The backend now includes authenticated tenant-scoped session API components, signed-webhook transport ingress, a tenant-encrypted address vault and a graceful worker loop, but it is still not a deployed or working recording service: no production Twilio event decoder/command adapter, consent IVR, media retrieval integration or carrier merge proof exists; a KMS-backed S3 storage adapter is implemented but not configured against a live bucket. More importantly, a manually merged SIM call may arrive as one mixed PSTN leg; this creates a consent-verification and channel-attribution problem that backend work cannot solve.

**Recommended product decision:**

1. Keep the native-call companion/import capability as a bounded foundation, not as the headline promise.
2. Treat SIM-call conference merge and external accessories as feasibility experiments. Do not commit production engineering or claim compatibility before physical evidence.
3. Evaluate app-owned VoIP as a separate product proposition, not as a hidden implementation detail or a workaround advertised as native SIM recording.
4. Do not choose a launch country, customer segment, price, or go-to-market channel until discovery interviews and legal review identify a viable wedge.

## 2. Product problem and jobs to be done

The underlying user job is not simply "record a call." A user may need to:

- Preserve an accurate record of an important conversation.
- Recall commitments, dates, instructions and decisions.
- Produce an auditable record for a business process.
- Search, export or share a recording without losing control of the original.
- Know before a call whether recording is actually supported and lawful.
- Avoid surprise recording, accidental disclosure, data leakage and uncertain retention.

These jobs have different buyers and acceptance criteria. Consumer convenience, professional documentation, regulated evidence retention and business call QA must not be combined into one persona or one launch claim.

### Candidate segments (hypotheses only)

| Segment | Job / pain hypothesis | Likely must-have | Principal blocker | Current status |
|---|---|---|---|---|
| Independent professionals and consultants | Preserve client instructions and commitments from mobile calls | Fast, reliable capture; export; search; predictable consent | Native SIM capture may not be available; legal duties vary | Unvalidated |
| Small sales/service teams | Keep records of customer calls and handoffs | Team access, CRM workflow, retention policy, audit trail | App-owned VoIP or enterprise telephony integration may be required | Unvalidated |
| Consumers in regions where Apple recording is unavailable | Record important personal calls | Simple setup, low price, broad carrier coverage | No universal public iOS capture path; legal restrictions | Unvalidated |
| Compliance-led organizations | Demonstrate consent, access control, retention and deletion | Policy controls, audit, residency, legal approval | High assurance, procurement and integration burden | Unvalidated |
| Accessory buyers | Capture calls without relying on app access to Phone audio | Proven two-way accessory signal path and easy retrieval | Hardware feasibility, certification, cost and support matrix | Unvalidated |

No segment is selected. Do not infer demand from the fact that a technical workaround exists or that competitor apps are listed in an app store.

## 3. Product concepts that must remain separate

| Concept | What the user actually gets | Strength | Critical limitation | Recommendation |
|---|---|---|---|---|
| Companion / recording library | Imports a file the user already obtained; validates, stores, plays, exports and deletes it | Most mature software in this repository; avoids private API claims | Does not create a recording; weak standalone differentiation | Keep as foundation / possible utility |
| Native SIM-call conference bridge | Attempts to merge a carrier call with a provider leg and records server-side | Could capture without Phone.app interception | Carrier-specific; merge may mix both speakers into one provider leg; consent may be impossible to verify on that topology | Feasibility gate only |
| External accessory | Hardware independently captures the required call signals; app manages/retrieves files | Could bypass app-only audio-access limitation | No accessory has been physically certified; hardware and certification costs unknown | Prototype only after signal-path proof |
| App-owned VoIP | User places/receives calls through an app-controlled media path | Strongest technical control over media, consent and channels | It is a different calling product; users must change their calling behavior | Evaluate as a separate product |
| Carrier recording service | Carrier/network provides recording capability | Potentially robust if a commercial API/contract exists | Market, plan, access and contract dependence | Research per named carrier only |

## 4. Market and platform reality (desk research)

### 4.1 Apple platform boundary

- Apple's current iPhone guide describes user-started recording for eligible one-to-one calls, with an audible notice to both participants and storage in Notes.
- The same guide currently lists the European Union, Iran and Oman among regions where Apple's built-in call recording is unavailable.
- The platform feature is not a public API for third-party apps to read Phone.app live audio or silently import its private recording store.
- CallKit is for integrating an app's own calling experience; it does not authorize interception of native Phone calls.

**Product consequence:** regional unavailability is a potential customer pain signal, not proof that this app can solve the problem. The product must not imply that it can unlock a system feature Apple withholds.

### 4.2 Competitor and substitute landscape

The actual alternatives users compare are:

1. Apple's native Phone recording where available.
2. Third-party conference-bridge recorder apps, whose real availability depends on carrier merge support and workflow constraints.
3. Carrier-provided recording products or enterprise telephony platforms.
4. Separate hardware recorders and speakerphone workflows.
5. App-owned VoIP and business phone systems.
6. Manual notes, CRM notes and meeting/call-summary tools.

A 2026 third-party comparison of iPhone recorder apps reports conference-call workflows and materially different pricing/quality among products, but it is secondary evidence and does not prove any carrier's compatibility. Competitor listings or marketing claims are not substitutes for controlled tests. Before selecting a segment, conduct a structured teardown of at least five products in the target market: setup steps, supported regions/carriers, inbound/outbound behavior, recording notice, failure handling, export, retention, privacy policy, subscription price and recent user complaints.

**Competitive implication:** "records calls on iPhone" is not a defensible differentiator by itself. A viable wedge would need to be demonstrated, for example: a verified compatibility cohort, unusually reliable workflow, privacy/local-storage advantage, a business-specific integration, or a distinct accessory experience.

### 4.3 Legal and trust are product requirements

- Apple's App Review Guidelines require explicit consent and a clear indication when recording user activity.
- Germany's Data Protection Conference has stated that, in general, effective consent for recording a phone conversation requires asking the external participant before recording and obtaining an unambiguous affirmative response; a mere opt-out opportunity is not sufficient. This is guidance, not a substitute for legal advice on a particular deployment.
- Oman's Personal Data Protection Law includes explicit-consent and transparency requirements for processing personal data. Separate telecommunications/criminal-law rules may also apply.
- The lawful basis, notice, retention, access, data residency, employee monitoring, cross-border processing and deletion obligations depend on the launch jurisdiction and use case.

**Product consequence:** no launch market or recording flow should be approved based on a generic "beep" or a single global consent checkbox. Jurisdiction-specific counsel must approve the exact call flow and data lifecycle.

## 5. Evidence register and confidence

| Claim | Classification | Evidence tier | Confidence / boundary |
|---|---|---|---|
| Ordinary third-party iOS apps cannot use a public API to tap Phone.app's private live cellular audio | Documented platform boundary | Primary platform documentation / Apple DTS research already recorded in repo | High for the current public API boundary; re-check each major iOS release |
| Apple built-in call recording is unavailable in the EU, Iran and Oman in the current guide | Documented | Current Apple Support page, accessed 2026-11-20 | High for the current published guide; availability can change |
| User-mediated import/library functionality is implemented in main | Observed in repository | Code and merged CI history | High for software scope; does not prove capture |
| Conference merge can work for some carrier/device configurations | Hypothesis / market precedent | Secondary competitor research and provider documentation | Low until physical carrier tests |
| A merged cellular call will preserve separately attributable local/remote channels | Hypothesis | No physical evidence | Unknown; must not be assumed |
| A selected HFP accessory can capture both directions on a named iPhone tuple | Hypothesis | Accessory design research only | Unknown; no certified accessory |
| A specific segment will pay for this product | Hypothesis | No customer evidence | Unknown |
| App-owned VoIP is a viable commercial alternative | Technical hypothesis | Provider documentation and app-owned media architecture | Not market validated; requires customer discovery and legal review |

### Primary / supporting sources reviewed

- Apple Support, *Record and transcribe a call on iPhone*, current iOS 27 guide: https://support.apple.com/guide/iphone/record-and-transcribe-a-call-iph57c6590e9/27/ios (accessed 2026-11-20).
- Apple, *iOS and iPadOS 27 Feature Availability*: https://www.apple.com/ios/feature-availability/ (accessed 2026-11-20).
- Apple, *App Store Review Guidelines*: https://developer.apple.com/app-store/review/guidelines/ (re-check before submission).
- German Data Protection Conference, *Aufzeichnung von Telefongesprächen*, 2018 decision: https://www.bfdi.bund.de/SharedDocs/Downloads/DE/DSK/DSKBeschluessePositionspapiere/DSK_20180323_Beschluss_Telefongespraeche.pdf (accessed 2026-11-20).
- Sultanate of Oman, Royal Decree 6/2022, Personal Data Protection Law: https://decree.om/2022/l20220006/ (accessed 2026-11-20).
- Secondary competitor scan: https://recordphonecall.com/apps/iphone-call-recorders/ (reviewed 2026-11-20; use as a discovery lead, not as primary evidence).
- Repository technical evidence: [recording pathway matrix](recording-pathways.md), [iPhone capture pathway research](iphone-capture-pathways-2026-11.md), [physical-device protocol](../engineering/physical-device-test-protocol.md), [accessory assessment](../testing/accessory-compatibility-assessment.md), [executable roadmap](../engineering/executable-product-roadmap.md).

## 6. Critical assumptions to test

| ID | Assumption | Cheapest falsification method | Pass signal | Fail / stop signal |
|---|---|---|---|---|
| PV-01 | A narrowly defined segment experiences this problem frequently enough to seek a dedicated solution | 15–20 problem interviews in one segment, not a generic survey | At least 10 describe a recent concrete workaround/problem without prompting | Most describe a rare or low-priority inconvenience |
| PV-02 | The proposed workflow is materially better than existing substitutes | Moderated prototype tests against current workaround | At least 8/10 complete the critical task and prefer it for a stated reason | Users prefer Apple/native or existing tools, or setup friction dominates |
| PV-03 | Users will pay at a sustainable price | Pricing interviews followed by paid pilot/deposit test | At least 5 qualified buyers accept a real paid pilot or documented procurement step | Positive verbal feedback but no paid commitment |
| PV-04 | At least one capture pathway works for the intended segment and market | Physical tests using consenting participants and authorized SIMs | Three repeatable two-way positive calls on an exact tuple for feasibility; 20 consecutive runs before production support | One-way audio, unverifiable consent, unstable merge, or no eligible carrier |
| PV-05 | The workflow can be lawful and trusted in the launch jurisdiction | Written review of the exact flow, notices, roles and retention | Counsel confirms a feasible lawful design with documented obligations | No viable consent mechanism or unacceptable legal exposure |
| PV-06 | Support cost and provider/accessory economics leave positive gross margin | Obtain provider quotes, number availability, support burden and hardware BOM | Conservative unit economics meet owner-set margin target | Variable call, support, hardware or compliance costs exceed willingness to pay |
| PV-07 | Users trust the storage and deletion model | Prototype test plus privacy/security review | Users understand who can access data, where it is stored and how to delete it | Trust objections cannot be mitigated without undermining product value |

These are proposed validation thresholds, not achieved results. Interview counts and conversion thresholds must be adjusted if the target segment is very small or enterprise-led.

## 7. Customer discovery protocol

### Recruit one segment at a time

Do not mix consumer, consultant, sales-team and compliance interviews into one average. Start with one candidate segment and recruit people who made or received relevant calls in the last 30 days.

### Interview questions (ask about past behavior)

1. Tell me about the last call you needed to remember or prove later.
2. What exactly did you need to preserve, and why?
3. What did you do immediately before, during and after that call?
4. What failed or took time in your current workaround?
5. How often did this happen in the last month?
6. What did the failure cost you (time, money, lost work, risk)?
7. Which tools or services have you already tried or paid for?
8. Who decides whether a call can be recorded, and what notice/consent process do you follow?
9. Where must the recording be stored, who may access it, and when must it be deleted?
10. What would make you reject a solution even if it worked technically?

Do not lead with the proposed feature or ask "would you use this?" Record exact past examples, current workarounds, frequency, buyer, budget owner, objections and follow-up commitment.

### Prototype test

Show a clickable or paper prototype only after the problem interview. Test the complete user journey: understand availability, start/prepare a call, disclose and obtain consent, handle unsupported configuration, verify completion, find/play/export/delete the artifact. Observe task completion without coaching. Do not use a simulated "recording succeeded" state unless the prototype clearly labels it as simulated.

### Evidence record

For each interview/test record:
- anonymized participant ID and segment;
- recruiting source and date;
- role / buying authority (not unnecessary personal data);
- last real incident and frequency;
- existing workaround and cost;
- exact objections and trust requirements;
- observed prototype task outcomes;
- willingness-to-pay evidence (verbal, written pilot, deposit or paid pilot distinguished);
- follow-up commitment;
- consent for research notes and retention/deletion date.

Do not store call recordings, phone numbers or sensitive personal content in the research repository.

## 8. Product decision gates

### Gate A — Problem validation
- [ ] One segment selected with a clear buyer and user.
- [ ] 15–20 interviews completed for that segment.
- [ ] Repeated recent problem and existing workaround evidenced.
- [ ] Frequency and consequence justify a dedicated workflow.
- [ ] No segment-wide demand claim based only on surveys or competitor popularity.

### Gate B — Solution validation
- [ ] End-to-end prototype tested with at least 10 target users.
- [ ] Critical tasks completed without coaching.
- [ ] Unsupported/failed recording states are understood and trusted.
- [ ] User prefers the workflow to their current workaround for a specific reason.

### Gate C — Technical feasibility
- [ ] A lawful capture pathway passes the physical-device acceptance protocol.
- [ ] Both local and remote speech are independently intelligible.
- [ ] Three successful repetitions establish feasibility on the exact tuple.
- [ ] Twenty consecutive successful sessions and interruption scenarios pass before declaring a tuple production-supported.
- [ ] Carrier/accessory/region limitations are published explicitly.

### Gate D — Commercial validation
- [ ] At least five qualified buyers accept a paid pilot, deposit, or formal procurement step.
- [ ] Pricing is tested against actual alternatives and usage frequency.
- [ ] Provider, support, storage, compliance and hardware costs are included.
- [ ] Conservative unit economics meet the product owner's explicit margin target.

### Gate E — Legal and trust validation
- [ ] Launch jurisdiction and user/business roles are explicit.
- [ ] Written legal/privacy review approves the actual consent and disclosure flow.
- [ ] Retention, access, export, deletion, data residency and incident handling are defined.
- [ ] App Store and any carrier/accessory program requirements are reviewed.

**No-go rule:** do not fund production-scale bridge, hardware or App Store launch work if Gate A fails or no feasible lawful capture path exists for the selected segment. Re-scope to a separate VoIP product only if customers validate that changed job and calling behavior.

## 9. Unit economics to collect (do not invent values)

For every candidate workflow, calculate:

- revenue per active user/team and paid conversion;
- provider call minutes, phone numbers, recording, storage, egress and transcription costs;
- failed setup/merge attempts and support contacts per successful recording;
- hardware BOM, certification, warranty, returns and logistics if accessory-led;
- security, legal, privacy, insurance and data-residency costs;
- gross margin after variable usage and support;
- customer acquisition cost and payback period.

Obtain current written quotes for the exact target country and usage profile. Public provider rate cards are not a substitute for number availability, regulatory eligibility, recording configuration or actual account pricing.

## 10. Current product recommendation and next work

**Current recommendation:** continue only the already-built companion/library foundation and bounded feasibility research. Do not claim the native SIM capture problem is solved. Do not start a broad production Twilio integration solely because the backend foundation exists.

Next actions, in order:

1. Owner selects one initial country/region and one candidate customer segment.
2. Recruit and complete the first 15–20 problem interviews; record evidence against PV-01.
3. In parallel, run the minimum physical conference-merge test on an authorized iPhone/SIM/carrier with two consenting participants; inspect actual media and consent topology before adding provider-specific production work.
4. If the conference route fails, stop treating it as the default native-SIM path and compare accessory vs. app-owned VoIP against the validated user job.
5. Test a prototype and real paid pilot before committing pricing, production infrastructure or marketing.

### What is complete vs. still open

| Workstream | Result as of 2026-11-20 |
|---|---|
| Platform/API desk research | Completed for current source snapshot; re-check before release |
| Technical pathway inventory | Completed as a research baseline |
| Companion/import software foundation | Implemented in main; not a capture solution |
| Provider foundation and consent sequencing | Domain/outbox, tenant-scoped API component, encrypted address vault, signed webhook transport, worker loop and KMS-backed S3 adapter implemented; no production decoder/adapter, deployed service or live call |
| Physical carrier/device capture | Not tested / not proven |
| Accessory signal path | Not tested / not certified |
| Customer problem validation | Not done |
| Prototype usability validation | Not done |
| Willingness to pay / paid pilot | Not done |
| Market selection and unit economics | Not done |
| Jurisdiction-specific legal approval | Not done |

**Overall status: Product validation is not complete.** The desk-research phase is complete enough to make a bounded technical/product decision; customer demand, commercial viability and real-world capture remain hard gates. This status must not be changed to "validated" until the corresponding evidence exists.
