# ADR-055: No Concurrent File Access

- Date: 2026-02-21
- Status: Accepted
- Decision: Concurrent agents (cc, cx, gm) are absolutely prohibited from accessing the same file simultaneously. File conflict prevention is mandatory before parallel execution.
- Rationale: Concurrent writes to the same file cause silent corruption. This is a physics-level constraint, not a policy preference.
- Outcome: L1 hard rule, enforced by session lock system

## Simondon Mapping
Individuation requires clear boundaries — concurrent modification destroys the integrity of the individuation process.
