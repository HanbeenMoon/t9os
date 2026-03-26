# ADR-041: Logging Standard Format

- Date: 2026-02-21
- Status: Accepted
- Decision: All work logs follow `YYYYMMDD_AGENT_NNN_HHMMSS_taskname.txt` format. Logs must include task name, start/end time, commands executed, results, and files created/modified.
- Rationale: Consistent log format enables automated parsing, cross-session search, and retrospective analysis.
- Outcome: Standardized log format across all agents

## Simondon Mapping
Reproducibility of individuation — logs are the trace that allows past individuations to be reconstructed and learned from.
