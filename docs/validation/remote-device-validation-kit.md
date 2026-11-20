# Remote physical-device validation kit

**Status:** ready-to-run external test protocol; no physical-device evidence has been submitted.  
**Purpose:** obtain real carrier, device, audio-route and two-way recording evidence without pretending an iOS Simulator or browser device farm can reproduce cellular call merge.

## Why a remote tester is the substitute

A simulator can validate UI and state logic but cannot validate a carrier's native cellular add-call/merge behavior, physical Bluetooth HFP routing or an acoustic path. If the project owner does not have the required hardware and test SIMs, use a paid, consented crowdtester or a partner who already has the exact carrier/device combination. A generic real-device cloud farm is not an adequate substitute unless it supplies active SIM service and permits real PSTN calls.

## Minimum tester setup

- Two physical iPhones (the local and remote endpoints), each with a working test SIM/eSIM and a distinct phone number.
- A third line is optional for testing call waiting/hold.
- One named carrier and plan, exact country/region, exact iOS version/build and device model.
- A Bluetooth HFP accessory and wired headset for route tests; speaker/receiver routes for acoustic comparison.
- A second human participant who has read the test notice and explicitly agrees before each recording test.
- A private evidence channel agreed with the project owner. Never attach personal call audio or phone numbers to public GitHub issues.

## Execution sequence

1. Run the companion app import/playback tests first; this proves only the archive workflow.
2. Run three outgoing and three incoming baseline attempts using the conference-bridge path.
3. For every run, follow physical-device-test-protocol.md and speak only the synthetic phrase set.
4. Test merge rejection and no-answer cases. A rejected merge must remain a failed/incomplete session, never a successful recording.
5. Repeat the baseline with Bluetooth HFP, wired headset and speaker/receiver routes.
6. Record both endpoints' subjective intelligibility and whether the two audio channels contain the expected independent speech.
7. Hash the WAV locally, submit only the checksum and sanitized metadata to the evidence record, and delete the raw artifact after review unless a separately approved secure transfer is needed.
8. Repeat the exact configuration on another day before calling it feasible.

## Tester deliverables

- One completed evidence row per attempt from the protocol template.
- Sanitized screenshots of app state transitions and carrier merge UI (no phone numbers or contact names).
- Device model, iOS build, carrier, plan class, SIM type, network mode and route.
- Pass/fail/inconclusive classification for each run.
- SHA-256 of the locally reviewed recording, channel count, duration, sample rate, activity in each channel and reviewer note.
- Confirmation that all participants consented and that the test artifact was deleted after review.

## Acceptance

- Feasibility: at least three successful core attempts on the same exact tuple, with all failures retained.
- Bounded support claim: at least 20 consecutive successful core attempts plus interruption and route-change scenarios on the same exact tuple.
- Any different iPhone, iOS build, carrier, plan, country, SIM mode or route is a different tuple and needs its own evidence.

## Recruitment brief (copy/paste)

> We need a manual iOS cellular-call recording feasibility tester. You must have two physical iPhones and two working SIM/eSIM lines on the named carrier, plus a second consenting participant. You will perform short test calls using only synthetic spoken phrases, follow a written test plan, and submit sanitized device/carrier metadata and pass/fail observations. No personal or confidential conversations are allowed. The work includes outgoing/incoming calls, carrier add-call/merge, merge rejection, Bluetooth HFP, wired headset and speaker/receiver routes. You must not upload raw audio to public sites. The project owner will agree on a private evidence-transfer and deletion process before the test. Please state device models, exact iOS builds, country, carrier/plan and audio accessories before accepting.

Do not hire a tester or incur costs without an approved budget and written test scope. This kit makes the work executable; it does not mean the physical tests have been performed.
