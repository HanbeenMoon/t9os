# ADR-052: IPC Cross-Session Communication

- Date: 2026-03-16
- Status: Accepted
- Decision: Implement inter-session communication via `lib/ipc.py`. When one session saves a preindividual to `field/inbox/`, IPC notifies other active sessions. Each session's conversation is independent, but async filesystem-based communication is available.
- Rationale: Concurrent sessions need coordination without coupling.
- Outcome: `lib/ipc.py`

## Simondon Mapping
Transduction between concurrent individuations — information propagates from one session's domain to another's.
