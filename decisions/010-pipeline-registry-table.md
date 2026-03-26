# ADR-010: Pipeline Registry Table

- Date: 2026-03-16
- Status: Accepted
- Decision: Register all pipelines/tools in markdown tables across CLAUDE.md, L1, and memory simultaneously. "Unrecorded = nonexistent."
- Rationale: In multi-session operation, the biggest failure mode is one session creating a tool that another session doesn't know about, leading to duplicate Builds.
- Outcome: Mandatory 3-location simultaneous update on any new pipeline creation

## Simondon Mapping
Reproducibility as associated milieu — the registry ensures that every individuation (pipeline creation) is visible across the entire system environment.
