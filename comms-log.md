---
lab4_comms:
  awareness: 2026-10-12T06:40:09Z
  detection: 2026-10-12T06:39:19Z
  classification: 2026-10-12T06:40:09Z
  nis2:
    early_warning_due: 2026-10-13T06:40:09Z
    notification_due: 2026-10-15T06:40:09Z
    notification_sent: 2026-10-12T08:00:00Z
    final_report_due: 2026-11-12T08:00:00Z
  ksc:
    early_warning_due: 2026-10-13T06:39:19Z
    notification_due: 2026-10-15T06:39:19Z
    notification_sent: 2026-10-12T08:00:00Z
    final_report_due: 2026-11-12T08:00:00Z
  dora:
    initial_due: 2026-10-12T10:40:09Z
    initial_sent: 2026-10-12T06:50:00Z
    intermediate_due: 2026-10-15T06:50:00Z
    intermediate_sent: 2026-10-14T15:00:00Z
    final_due: 2026-11-14T15:00:00Z
  log:
    - {at: 2026-10-12T06:50:00Z, to: financial supervisor, what: DORA initial major-incident notification}
    - {at: 2026-10-12T07:00:00Z, to: national CSIRT, what: NIS2 early warning}
    - {at: 2026-10-12T08:00:00Z, to: national CSIRT, what: NIS2 and KSC incident notifications}
    - {at: 2026-10-14T15:00:00Z, to: financial supervisor, what: DORA intermediate report}
    - {at: 2026-11-12T08:00:00Z, to: national CSIRT, what: NIS2 and KSC final reports}
---
<!-- ai-generated: 80% - prepared with Copilot; all deadline arithmetic follows INCIDENT-SPEC I-30. -->

# Communications log: the regulators' clocks

## The three instants you defend

Detection is the recorded alert start at 06:39:19Z. Awareness and DORA classification are both 06:40:09Z, when the on-call acknowledged the P1 ticket and had confirmation of user-facing checkout impact. This is a conservative, evidence-backed point at which the incident was known to be significant and major; it avoids backdating either judgement to the injector's hidden onset.

## The log

The DORA initial report is scheduled at 06:50Z, before its 10:40:09Z deadline. The NIS2 early warning is sent at 07:00Z; NIS2 and KSC incident notifications follow at 08:00Z, well before their respective 72-hour deadlines. The DORA intermediate report is sent on 14 October at 15:00Z, before its 15 October 06:50Z deadline. NIS2 and KSC final reports are scheduled for 12 November at 08:00Z. The DORA final report is scheduled for 14 November at 15:00Z. All instants are UTC; no weekend extension is applied.
