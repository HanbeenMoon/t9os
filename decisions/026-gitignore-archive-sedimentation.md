# ADR-026: Gitignore Overhaul + Archive Sedimentation

- Date: 2026-03-17
- Status: Accepted
- Decision: Redesign `.gitignore` to exclude local-only directories from git tracking. Completed/inactive projects move to archive and are removed from git (sedimentation pattern).
- Rationale: Hundreds of untracked files create noise. Completed projects cluttering the active workspace violate the sedimentation principle.
- Outcome: Clean `.gitignore`, archive sedimentation pattern

## Simondon Mapping
Sedimentation — completed structures sink into background storage, remaining searchable but no longer occupying active attention.
