# ADR-002: Simondonian Phase Transition Model

- Date: 2026-03-16
- Status: Accepted
- Decision: Manage all entity lifecycles through 12 states based on Simondon's individuation theory (preindividual, impulse, tension_detected, candidate_generated, individuating, stabilized, split, merged, suspended, archived, dissolved, reactivated) with strict transition graph enforcement.
- Rationale:
  - The conventional TODO/DOING/DONE paradigm ignores input potential. User inputs are not "tasks" — they are desires, tensions, possibilities.
  - Simondon's core insight: the individual is not the starting point; the process is primary and the individual is a partial result. The preindividual resists premature classification.
  - Dissolved is not deletion — it is sedimentation. Everything remains searchable.
- Alternatives rejected:
  - GTD-style task management (kills preindividual potential)
  - Kanban board states (too rigid, no re-individuation path)
- Outcome: 12-state machine with explicit transition rules in L1/L2.

## Simondon Mapping
The entire state machine is a direct implementation of Simondon's individuation process — from preindividual supersaturation through metastable tension to individuated stabilization.
