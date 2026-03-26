# ADR-027: Claude Code as Control Tower

- Date: 2026-02-21
- Status: Accepted
- Decision: Designate Claude Code (cc) as the AI orchestration control tower, replacing web Claude AI. Three-role system: cc (judgment/strategy/routing), cx/Codex (code/docs), gm/Gemini (OCR/bulk).
- Rationale: Web Claude resets context per conversation, wasting tokens on re-briefing. CLI-based Claude Code maintains persistent context and can orchestrate other agents.
- Outcome: Three-agent architecture documented in L1

## Simondon Mapping
Individuation of the technical system itself — the agent ecosystem differentiates from a single generalist into specialized roles.
