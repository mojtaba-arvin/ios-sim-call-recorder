# Twilio bridge unit-economics baseline

**Snapshot:** 2026-11-20  
**Status:** published vendor-rate model; not a complete COGS model or evidence of willingness to pay.  
**Currency:** USD; rates are subject to change and exclude tax.

## Inputs from Twilio's published pricing

- US/Canada outbound local voice: **$0.0140 per minute**.
- Germany outbound mobile voice: **$0.0420 per minute**; Germany local voice: **$0.0283 per minute**.
- Conference: **$0.0018 per participant-minute** in both regions.
- Recording: **$0.0025 per recording-minute**.
- Recording storage: **$0.0005 per stored recording-minute per month**.
- Local number rental shown on the regional price pages: US **$1.15/month**, Germany **$1.35/month**.
- Twilio removed the historical 10,000-minute recording-storage free tier from July 2026; stored recording minutes are billable.

Sources:
- [Twilio US Voice pricing](https://www.twilio.com/en-us/voice/pricing/us)
- [Twilio Germany Voice pricing](https://www.twilio.com/en-us/voice/pricing/de)
- [Twilio Conference pricing](https://www.twilio.com/en-us/voice/conference/pricing)
- [Twilio recording-storage pricing update](https://help.twilio.com/articles/56876349198619)

## Example: two-party, ten-minute recorded bridge

Assumptions:
- Exactly two human participants.
- The service places one outbound consent call to each participant, modeled at one minute per participant.
- After both consent, the service places two outbound conference participant calls, each connected for ten minutes.
- Recording lasts ten minutes and is stored for one month.
- Both participants are billed as outbound destinations at the regional rate. Conference and recording charges are additional.
- No retries, failed attempts, taxes, support, cloud compute, database, S3/KMS, App Store fees, payment fees or legal costs are included.

| Variable cost | US / Canada | Germany |
|---|---:|---:|
| Consent calls: 2 × 1 min × outbound rate | $0.028 | $0.084 |
| Conference legs: 2 × 10 min × outbound rate | $0.280 | $0.840 |
| Conference: 2 × 10 participant-min × $0.0018 | $0.036 | $0.036 |
| Recording: 10 min × $0.0025 | $0.025 | $0.025 |
| First-month storage: 10 min × $0.0005 | $0.005 | $0.005 |
| **Estimated Twilio variable subtotal** | **$0.374** | **$0.990** |

This is a transparent lower-bound scenario, not a price quote. Voice billing rounds per call according to Twilio billing rules; actual consent-call duration, carrier routing, number type, retries and regional destination rates change the result. A bridge to a German mobile destination is materially more expensive than the US/Canada example.

## Commercial implications

1. A consumer subscription cannot be priced from the recording fee alone. Two outbound PSTN legs dominate this example, especially in Germany.
2. A free trial needs hard call-duration, retry and recording-retention limits to prevent abuse.
3. Paid-pilot pricing should be based on actual destination mix, median/95th-percentile duration, failed-call rate, retention period, cloud costs, support and compliance costs.
4. The unit model must be recalculated for the selected launch country and the actual number type before a paid pilot.
5. Do not infer willingness to pay from this cost model. Customer interviews and a paid commitment remain uncollected.

## Go/no-go inputs still missing

- One selected jurisdiction and customer segment.
- Real call-duration and failure distributions from an authorized pilot.
- AWS cost estimate from a deployed staging environment and observed media size.
- Support and acquisition cost.
- A signed paid-pilot commitment or procurement evidence.
