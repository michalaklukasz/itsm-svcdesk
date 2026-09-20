<!-- ai-generated: 80% - Claude Code drafted the initial service specification and I refined the conflict decisions -->
# Service specification for svcdesk

This specification records the required behaviour for the Lab 1 service desk API before implementation begins.

## Scope

- Create and list tickets via HTTP on port 8080.
- Validate inputs and return error objects for invalid requests.
- Compute priority from impact and urgency with VIP handling as a separate rule.
- Track the ticket lifecycle and reopen rules.
- Apply SLA targets using the configured clock policy.

## Conflicts resolved

- C1: P1 SLA clock uses the business-hours clock for all priorities.
- C2: closed tickets are immutable; reopening requires a new related ticket.
- C3: VIP tickets at P3/P4 are raised to P2 after the matrix calculation.

## Acceptance criteria

- `GET /health` returns `{"status":"ok","service":"svcdesk"}`.
- POST /tickets validates required fields and ignores server-owned or unknown fields.
- `GET /tickets` and `GET /tickets/{id}` list and fetch tickets correctly.
- State transitions follow the documented machine and invalid transitions return `409`.
- SLA values are calculated exactly for the chosen decision set and test clock vectors.
