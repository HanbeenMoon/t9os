# ADR-056: Notion to Local-First Migration

- Date: 2026-03-15
- Status: Accepted
- Supersedes: ADR-029
- Decision: Migrate entirely from Notion-based UI to local cc-centric operation. SQLite replaces Notion as the single source of truth.
- Rationale: Notion API instability, encoding issues, and external dependency made it a persistent source of bugs. Local-first eliminates an entire class of failure modes.
- Outcome: Full migration to SQLite + filesystem, Notion relegated to optional dashboard

## Simondon Mapping
The system's associated milieu shifts from a cloud-dependent environment to a local-first one — increasing autonomy and reducing environmental fragility.
