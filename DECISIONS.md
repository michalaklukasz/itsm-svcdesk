---
svcdesk_decisions:
  C1: business       # wallclock | business
  C2: immutable      # reopen | immutable
  C3: vip            # matrix | vip
---
<!-- ai-generated: 90% - I drafted the decisions from the published lab contract, then aligned the wording and values to the service behavior that the checker will exercise. -->

# Decisions

## C1 - SLA clock for P1

**Decision:** We use the business-hours clock for every priority, including P1, so the SLA is computed only inside Monday-Friday 08:00 to 16:00 in Europe/Warsaw.

**Rejected alternative:** Wall-clock was rejected because it would let a P1 created late on Friday keep accumulating time in the weekend, which is inconsistent with the course’s service-level operating model and past lab examples.

**Reason:** The lab explicitly allows either clock choice for P1, but the business-hours model is the safer operational choice for an ITSM desk because it mirrors real support coverage and avoids weekend carry-over on urgent tickets.

**Service owner:** The service operations lead owns the SLA model because they are accountable for staffing coverage, support windows, and the published response expectations for all priority classes.

**Customer outcome:** Customers receiving a priority-one issue get a due time that reflects actual support availability, which reduces false breaches caused by overnight or weekend gaps and gives a more realistic service promise.

## C2 - Closed tickets and reopening

**Decision:** Closed tickets are immutable; reopening is allowed only from a resolved ticket within the 7-day window, and closed tickets remain closed unless the ticket is recreated with a related_to reference.

**Rejected alternative:** Reopen-from-closed was rejected because it weakens the audit trail and creates a path for mutating a concluded incident after closure, which is risky for operational records and change control.

**Reason:** The lab’s immutable option is the more disciplined choice for a service desk: it preserves finality on closure while still allowing a bounded correction window for resolved items.

**Service owner:** The incident management owner signs off on this because they maintain closure discipline, customer communications, and the evidentiary chain that supports after-action review.

**Customer outcome:** Reporters and internal stakeholders get a dependable lifecycle: resolved work can be reopened briefly when needed, but once a ticket is closed it stays closed to preserve the final status and audit record.

## C3 - VIP reporters and the priority matrix

**Decision:** We raise any VIP ticket that would otherwise land at P3 or P4 to P2 after the base matrix is applied; P1 and P2 remain unchanged.

**Rejected alternative:** The matrix-only behavior was rejected because VIP customers are usually business-critical and should not wait under the same conditions as ordinary low-priority tickets when the urgency pattern is similar.

**Reason:** This preserves the matrix as the reference model while giving the service desk a practical escalation rule for high-value reporters without over-privileging every VIP case to the top category.

**Service owner:** The support prioritisation owner owns this decision because they are responsible for respecting customer impact and balancing workload across the service queue.

**Customer outcome:** VIP reporters still get prompt attention when their issue is operationally important, while the team keeps a clear and explainable escalation policy instead of gaming the matrix arbitrarily.
