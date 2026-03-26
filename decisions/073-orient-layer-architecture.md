# ADR-073: Orient Layer Architecture (OLA)

- Date: 2026-03-23
- Status: Accepted
- Decision: Add an Orient Layer to the PreToolUse hook chain, positioned after the hard gate. The Orient Layer structures soft gates (SRBB, philosophical alignment, full-scan principle) as branch conditions with explicit checklists and severity levels.
- Rationale: Soft gates were previously unstructured LLM prompts. Structuring them as YAML-defined routes with explicit triggers and checklists makes them auditable and consistent.
- Outcome: `constitution/orient_routes.yaml`, OLA Phase 0 logging

## Simondon Mapping
The Orient Layer is modulation made explicit — dynamic judgment (soft gates) structured into a reproducible, evolvable form.
