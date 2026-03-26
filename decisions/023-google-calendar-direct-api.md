# ADR-023: Google Calendar Direct API Integration

- Date: 2026-03-06
- Status: Accepted
- Decision: Integrate Google Calendar API directly using OAuth2 refresh token for two-way calendar sync. Entities with deadlines auto-appear as calendar events.
- Rationale: Calendar is a critical coordination tool. Manual deadline tracking is error-prone and creates meta-work.
- Outcome: `pipes/calendar_sync.py`, cron-scheduled 3x daily

## Simondon Mapping
Concretization — calendar sync is functional convergence between the entity lifecycle and external scheduling tools.
