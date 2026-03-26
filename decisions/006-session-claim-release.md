# ADR-006: Session Claim/Release for Conflict Prevention

- Date: 2026-03-16
- Status: Accepted
- Decision: Use project/file-level claim/release locking for multi-session operation. State recorded in `.session_locks.json` in human-readable format.
- Rationale: The designer runs multiple concurrent cc sessions (up to 3-day long sessions + parallel sessions). Same-file collisions are a practical reality.
- Outcome: `pipes/session_lock.py`, `t9_seed.py claim/release`

## Simondon Mapping
Associated milieu — session locks are part of the technical environment that conditions and enables individuation across concurrent processes.
