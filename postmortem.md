---
lab4_postmortem:
  ticket: "50ceffde-fa49-40b3-b4ca-957734d74bf7"
  detecting_alert: ShopCheckoutErrors
  onset: 2026-10-12T06:36:23Z
  detection: 2026-10-12T06:39:19Z
  acknowledgement: 2026-10-12T06:40:09Z
  recovery: 2026-10-12T06:44:19Z
  mttd_seconds: 176
  mtta_seconds: 50
  mttr_seconds: 476
  identified_flags: [paymentFailure, loadGeneratorFloodHomepage]
---
<!-- ai-generated: 80% - drafted with Copilot from the recorded snapshot, ticket, and re-executed PromQL evidence. -->

# Postmortem: checkout payment failures and homepage traffic surge

## Date

The recorded incident occurred on 12 October 2026; this postmortem was prepared after recomputing the snapshot clocks.

## Authors

Prepared by the on-call analyst with Copilot assistance, using the recorded incident and its published telemetry.

## Status

Complete for the recorded evidence; follow-up actions are proposed and remain to be assigned by the service owners.

## Summary

Checkout requests failed when payment charge calls began returning errors, while homepage traffic rose sharply. The detecting alert recovered 7 minutes 56 seconds after onset.

## Impact

At 06:42Z, checkout and payment each showed about 0.0321 failed calls per second. Frontend `GET /` traffic was 59.45 requests per second, compared with 0.0833/s at the healthy baseline. These are query rates, not estimates of unique users.

## Root Causes

Payment's internal `charge` span and checkout's payment-call client span failed together, supporting `paymentFailure`. Homepage `GET /` volume rose by over 700 times, supporting `loadGeneratorFloodHomepage`. The sealed third flag cannot be identified safely from these two symptoms, so it is not guessed here.

## Trigger

The injector's recorded onset was 06:36:23Z. The snapshot establishes when the fault began, but does not expose its sealed flag variants or the operator's exact flag-off commands.

## Resolution

The recorded alert run ended at 06:44:19Z after the recorded operator mitigated the incident. In a live response, disable the confirmed payment and homepage-load flags one at a time, verifying checkout errors and homepage request volume after each change; the snapshot does not establish their exact switch-off order.

## Detection

`ShopCheckoutErrors` detected the incident at 06:39:19Z, 176 seconds after onset. The ticket was acknowledged at 06:40:09Z, 50 seconds after detection. The recorded P1 ticket is the incident record; this document tracks the separate problem.

## Action Items

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Add a payment dependency error-rate panel with a link from the checkout page | mitigate | Payments on-call | ITSM-4301 |
| Add a frontend request-volume guardrail and a reviewed rollback runbook for load changes | prevent | Web platform | ITSM-4302 |
| Require the on-call timeline to record each flag change and its measured effect | process | Incident commander | ITSM-4303 |

## Lessons Learned

### What went well

The request and span metrics separated payment dependency errors from the independent homepage traffic surge, and the ticket acknowledgement was present in telemetry.

### What went wrong

The recorded AI transcript used incorrect historical query timestamps in several tool calls, so its final claims had to be re-executed at valid incident instants before they were admitted to the ledger.

### Where we got lucky

The snapshot includes a healthy baseline and the recovery run, allowing both the predictions and the alert clocks to be checked without relying on recollection.

## Timeline

- 06:31:23Z — healthy baseline evaluation; payment charge errors and homepage traffic predictions are empty.
- 06:36:23Z — recorded fault onset.
- 06:39:19Z — `ShopCheckoutErrors` fires and detects the incident.
- 06:40:09Z — the P1 ticket is acknowledged.
- 06:42:00Z — re-executed ledger queries confirm payment and checkout errors and the homepage traffic surge; no AI hypothesis was used to issue a live change.
- 06:44:19Z — the detecting alert's first firing run ends; this is the recomputed recovery.

## Supporting information

The ticket id is `50ceffde-fa49-40b3-b4ca-957734d74bf7`. `itsmlab incident 4` recomputes onset 06:36:23Z, detection 06:39:19Z, acknowledgement 06:40:09Z, recovery 06:44:19Z, MTTD 176s, MTTA 50s and MTTR 476s. The AI ledger records each final transcript claim with a filtering PromQL query evaluated at 06:42:00Z and against the 06:31:23Z baseline. The homepage rate query is `sum(rate(traces_span_metrics_calls_total{service_name="frontend",span_name="GET /"}[5m]))`.

## Problem record

- Incident record: P1 ticket `50ceffde-fa49-40b3-b4ca-957734d74bf7`.
- Root cause: Payment charge failures and a homepage traffic surge affected the shop during the same recorded incident.
- Known error: Checkout does not isolate payment dependency failures from user-facing order placement errors.
- Workaround: Disable the confirmed failing feature flags individually and verify checkout errors and homepage traffic recover.
