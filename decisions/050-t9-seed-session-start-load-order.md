# ADR-050: Session Start Load Order

- Date: 2026-03-15
- Status: Accepted
- Decision: Session start must load context in order: L1 → L2 → WORKING.md → state.md. Session-start hook auto-runs seed engine reindex + daily.
- Rationale: Load order determines which rules and context the agent operates under. Incorrect ordering causes rule precedence violations.
- Outcome: `session-start.sh` hook with deterministic load sequence

## Simondon Mapping
The load order is the initial conditions of each individuation — the starting state of the preindividual field for that session.
