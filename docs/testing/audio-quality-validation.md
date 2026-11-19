# Physical call-audio validation protocol

**Status:** ready for controlled physical-device execution; no device/carrier result is claimed by this document.

## Safety and privacy

- Use test numbers and participants who have explicitly agreed to the recording test.
- Confirm the recording notice and affirmative consent required by the chosen pathway and local law.
- Do not test on customer calls or capture unrelated conversations.
- Keep raw recordings, phone numbers, contact names, provider URLs and account credentials outside GitHub issues, PRs, CI artifacts and ordinary logs.
- Analyze files locally. Share only redacted metrics and the exact compatibility tuple.

## Required compatibility tuple

Record these values for every run:

| Dimension | Required value |
|---|---|
| Device | Marketing model and exact model identifier |
| OS | iOS version and full build |
| Region | Device region setting, physical country and language |
| Carrier | Operator, carrier bundle if available, plan/tariff |
| SIM | Physical SIM/eSIM, dual-SIM, active voice line |
| Network | LTE/5G, VoLTE, Wi-Fi Calling, roaming |
| Call | Incoming/outgoing, one-to-one/conference, call duration |
| Route | Receiver, speaker, wired, Bluetooth HFP or named accessory |
| Accessory | Make/model, firmware, adapter, case/no-case, volume |
| Consent | Notice played, affirmative consent method, timestamp relative to recording |
| Artifact | Container, sample rate, channel count, duration, file size |

## Repeatable test procedure

1. Verify the participants, test numbers and consent before placing the call.
2. Record the complete compatibility tuple before each attempt.
3. Start with a short test call and confirm the intended route is active.
4. Have the local participant and remote participant speak distinct, pre-agreed phrases in alternating turns. Repeat at the beginning, middle and end to expose truncation and gaps.
5. Include simultaneous speech briefly to reveal gating/ducking behavior.
6. End the call normally, export the resulting artifact through the documented user flow and import it into the app.
7. Listen to the beginning, middle and end. Verify local and remote speech independently; do not infer speaker identity from stereo channel count.
8. Record duration, sample rate, channel count, clipping, silence gaps, echo, background noise, intelligibility and truncation.
9. Repeat the same configuration at least three times before marking it as a positive observation.
10. Change one compatibility dimension at a time when investigating a failure.

## Local WAV metrics

The repository tool `scripts/analyze_call_audio.py` computes per-channel RMS, peak level, clipping ratio, silent-window ratio and longest silent gap. It uses only Python's standard library and prints metadata/metrics; it does not upload or persist audio.

For an M4A or another format supported by FFmpeg, convert locally to PCM WAV while preserving the source channel count and sample rate:

```sh
ffmpeg -i input.m4a -map 0:a:0 -c:a pcm_s16le output.wav
python3 scripts/analyze_call_audio.py output.wav
```

The analyzer is an aid, not an acceptance oracle. A quiet speaker may fall below the silence threshold; non-silent noise may look active; metrics cannot identify a speaker or establish consent. Human listening against known phrases remains mandatory.

## Result classification

- **Confirmed:** at least three repeated positive runs for the exact compatibility tuple, with both voices independently intelligible and no disqualifying gaps/truncation.
- **Observed:** a positive result occurred but repeat count or evidence is incomplete.
- **Hypothesis:** based on documentation or expected topology only.
- **Rejected:** repeated tests or a platform/carrier contract rule out the proposed route for the exact configuration.

Do not generalize a result to other iPhone models, iOS builds, carriers, countries, plans, SIM configurations or accessories.

## Per-run result template

Copy this block into a private test log; publish only a sanitized version:

```text
Run ID:
Date/time:
Compatibility tuple:
Pathway:
Consent verified:
Notice heard:
Local phrase intelligible:
Remote phrase intelligible:
Both sides audible:
Container / sample rate / channels / duration:
Per-channel RMS / peak / clipping / silence:
Echo / noise / gaps / truncation:
Outcome: confirmed / observed / hypothesis / rejected
Failure details:
Repeat index (1 of 3, 2 of 3, 3 of 3):
```

## Current blockers

- Physical iPhone and carrier tests cannot be established by GitHub Actions or Simulator.
- Issue #20 is the controlling gate for Apple-native, wired, USB-C, Bluetooth and independent-recorder compatibility.
- Issue #18 is the controlling gate for SIM conference-bridge merge topology and provider channel semantics.
