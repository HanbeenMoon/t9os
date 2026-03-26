# ADR-016: Sediment Resurface Mechanism

- Date: 2026-03-19
- Status: Accepted
- Decision: `t9_seed.py resurface` command pulls sediment-state entities back to preindividual. Sedimentation is not deletion — it is potential sinking into background. A reactivation path must always exist.
- Rationale: In Simondon's ontology, sedimentation is not death. When conditions change, potential can reactivate. A one-way `transition → sediment` with no return violates this principle.
- Outcome: `resurface` command, random sediment surfacing in daily briefs

## Simondon Mapping
Residual preindividuality — sedimented entities retain their potential for future individuation, just as supersaturated solutions retain dissolved material.
