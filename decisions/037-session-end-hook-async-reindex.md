# ADR-037: Async Session-End Hook

- Date: 2026-03-17
- Status: Accepted
- Decision: Remove reindex from session-end hook or run it in background (subshell + disown). Remove `set -e` so individual failures don't abort the entire hook.
- Rationale: Synchronous reindex during session-end blocks the terminal for 10-30 seconds, creating poor UX.
- Outcome: Background reindex in `session-end.sh`

## Simondon Mapping
UX concretization — reducing friction in the session lifecycle mirrors the Zero Decision principle.
