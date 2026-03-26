# ADR-012: Automated Data Integrity Verification

- Date: 2026-03-19
- Status: Accepted
- Decision: `integrity_check.py` auto-verifies 6 items: DB connection, entity count, transition consistency, file synchronization, index integrity, schema version.
- Rationale: T9 OS is a hybrid system (SQLite + markdown + git). Data inconsistencies can develop silently (ghost entities, orphaned records, broken transition chains).
- Outcome: `pipes/integrity_check.py`, integrated into session-start hook

## Simondon Mapping
Associated milieu feedback — integrity checks are the system sensing its own environmental state and self-correcting.
