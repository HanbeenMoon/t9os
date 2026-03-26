# ADR-007: Seed Engine Single Entry Point

- Date: 2026-03-15
- Status: Accepted
- Decision: `t9_seed.py` is the single entry point for all entity management commands (capture, reindex, search, status, daily, transition, compose, approve, reflect, consolidate, history, relate, claim, release, check).
- Rationale: A single entry point means (1) new sessions only need to learn one tool, (2) DB access is centralized for schema consistency, (3) `self_check()` can validate schema on every operation.
- Outcome: ~900-line seed engine with 1000-line cap (growth in data and rules, not code)

## Simondon Mapping
The seed engine is the seed crystal in Simondon's supersaturated solution — the singular point from which individuation propagates.
