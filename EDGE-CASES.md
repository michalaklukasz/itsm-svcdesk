---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 90% - drafted with AI from the published event rules and checked against the service counts -->

# Edge cases in the practice event log

## E1 - clock skew produces a negative lead time

- What the log contains: Three commit/deployment pairs have commit timestamps later than the successful deployment that carried them.
- What a default definition would have done: It might drop those pairs or report negative seconds, changing the median based on clock drift rather than delivery.
- Why the rule is defensible: Keeping each shipped pair and clamping its duration to zero preserves the delivery evidence without claiming impossible negative work time.

## E2 - a revert of a revert

- What the log contains: Two commits revert earlier commits, including a commit that already reverted another change.
- What a default definition would have done: Counting each SHA as separate work would turn a correction chain into three changes and inflate the apparent amount delivered.
- Why the rule is defensible: The transitive original change identity represents the net work once, instead of treating undo operations as new product capability.

## E3 - a hotfix that never touched `main`

- What the log contains: Four distinct non-main commit SHAs are carried by production deployments in the observation window.
- What a default definition would have done: A branch filter would exclude these hotfixes and make production lead time look better by omitting real customer-facing work.
- Why the rule is defensible: Production exposure, not a branch label, determines whether a change belongs in the delivery metric.

## E4 - a deployment with zero linked commits

- What the log contains: Four in-window production deployments have an empty commits array.
- What a default definition would have done: It could discard the deployments or divide by zero, hiding release activity and corrupting rate denominators.
- Why the rule is defensible: A production deployment is still an operational event even when its provenance is missing; preserving it makes the data-quality gap visible.

## E5 - a deployment that failed and never recovered

- What the log contains: One in-window production failure has no resolved event for its covering incident.
- What a default definition would have done: It might invent a recovery at window end or omit the failure, understating unresolved risk on the dashboard.
- Why the rule is defensible: An open failure has no observed recovery duration, so it stays in the failure rate while remaining absent from the recovery-time median.

## E6 - overlapping incidents

- What the log contains: Eleven unordered pairs of distinct incident intervals overlap in time.
- What a default definition would have done: Merging or summing those intervals would double-count concurrent impact and exaggerate downtime for the person reading the metric.
- Why the rule is defensible: Each failed deployment is recovered against its earliest covering incident; overlap is recorded as a data characteristic, not additive outage time.

## Gaming demonstration

I improved `deployment_frequency_per_day` under R-11 from 2.000000 to 2.523810 deployments per day, a 26.19% increase. The event log keeps every original event, but all successful production deployments are moved later; 45 new empty production deployments are added inside the window. R-19 permits later deployment times and added events, while R-11 counts production deployments regardless of whether they carry commits. On the base work alone, `changes_delivered` falls from 65 to 0, so the dashboard reports a better frequency while real delivery within the window is measurably worse. A team rewarded for release-count targets could schedule ceremonial no-op releases and defer meaningful deliveries past the reporting boundary; the release manager or leadership dashboard owner would receive the apparent improvement, while customers and the engineers carrying the delayed work would bear the cost.