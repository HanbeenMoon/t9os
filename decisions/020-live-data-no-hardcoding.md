# ADR-020: Live Data Principle — No Hardcoding

- Date: 2026-03-05
- Status: Accepted
- Decision: All data displayed or used by the system must come from live sources (DB, API, filesystem). Hardcoded project lists, logs, and deadlines are prohibited. Dead data is removed at the source.
- Rationale: Hardcoded data decays silently. If the source of truth is a static string, it will inevitably diverge from reality.
- Outcome: All dashboard and briefing data sourced from live queries

## Simondon Mapping
Associated milieu — the system must sense its actual environment, not a frozen snapshot of it.
