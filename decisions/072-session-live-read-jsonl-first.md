# ADR-072: Session Data — JSONL First

- Date: 2026-03-23
- Status: Accepted
- Decision: Read session conversation data directly from JSONL. Markdown conversion is a byproduct, not a dependency. Do not wait for session end.
- Rationale: Waiting for conversion introduces unnecessary latency. JSONL is written to disk in real-time and is the ground truth.
- Outcome: `pipes/session_live_read.py`

## Simondon Mapping
Immediate access to preindividual data — delaying access delays individuation.
