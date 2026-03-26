# ADR-022: Infrastructure Status Monitoring

- Date: 2026-03-05
- Status: Accepted
- Decision: Implement healthcheck endpoints that monitor connectivity to all external services (GitHub, calendar, messaging, file sync) with online/offline status.
- Rationale: Silent infrastructure failures cause cascading problems. Proactive monitoring catches issues before they affect work.
- Outcome: `pipes/healthcheck.py`

## Simondon Mapping
Associated milieu sensing — monitoring infrastructure state is the system perceiving its own technical environment.
