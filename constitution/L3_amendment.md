# L3: Amendment Rules — When and How to Modify L1 and L2

> v0.2 — Simondonian overhaul (2026-03-16)

## Core Principle

> "Not a finished OS, but a hypothetical OS that can modify its own rules at any time."
> "Modulation: not stamping a form once, but continuous, perpetually variable self-formation."

## Amendment Triggers

1. **Reality mismatch**: A rule conflicts with actual work in 3+ cases
2. **Designer directive**: Explicit request to change a rule
3. **New tool discovery**: A better "Buy" option found via SRBB
4. **Performance degradation**: Token waste, output quality drop, meta-work ratio increase
5. **Concretization shift**: Integration level between tools has materially changed

## Amendment Procedure

1. Describe the current rule's problem
2. Draft the amendment
3. Analyze impact scope (check for contradictions across L1/L2/CLAUDE.md/memory)
4. Record the amendment (see log below)
5. Apply — update all three locations simultaneously (L1/L2 + CLAUDE.md + memory)

## Concretization Level Measurement

Simondon's "concretization": evolution from abstract (each component independent) to concrete (multi-functional integration between components).

| Level | Description | Example |
|-------|-------------|---------|
| 1-Abstract | Each tool runs independently, manual handoffs | Agent A copy-pastes results to Agent B |
| 2-Connected | Automated connections exist between tools | Agent A calls Agent B directly, logs auto-saved |
| 3-Integrated | One task automatically traverses multiple tools | Session end triggers log + memory + sync simultaneously |
| 4-Concrete | Tool boundaries dissolve, system operates as organism | Environment change → auto-rerouting → artifact |

## Modulation Principle

- Amendment is not "error correction" — it is part of **continuous modulation**
- The feeling that a rule has become rigid is itself an amendment trigger
- Formal completeness is not the goal — variability is
- Amendment frequency too high (3+/week) → structural problem, inspect L3 itself

## Non-Retroactivity Principle (Ruckwirkungsverbot)

### Principle

When L1/L2/L3 rules are amended, **actions performed before the amendment are evaluated under the rules that were in effect at the time of action**, not the amended rules.

The core value is **planability**: if the agent makes 100 decisions trusting L1 rules during a session, and a post-session rule change retroactively invalidates all 100, the agent can never act with confidence. This paralyzes the system.

### Application Rules

1. **Intra-session safety**: If L1/L2 changes mid-session (amended by another session, propagated via live-digest), the current session may complete remaining work under **session-start rules**. New rules apply to **new work units** after awareness.

2. **No retroactive guardian audits**: When G3 re-audits past commits after a rule change, violations must not be judged by **rules that did not exist at commit time**. Audit baseline is the commit's schema_version.

3. **Exceptions** (retroactive application permitted):
   - Security vulnerabilities (OWASP P0): security risk exists prior to and independent of rules
   - Explicit retroactive directive from the designer
   - Ontological violation (G2-B VIOLATION): Simondonian principles are above L1

4. **Amendment log must specify retroactivity**: Every amendment log entry includes `retroactive: YES/NO`. Default is NO.

### On Violation

If a retroactive violation judgment occurs, the agent **suspends** the judgment and reports to the designer. No automatic remediation.

## Meta-Rule

- L3 itself is subject to amendment (modulation of modulation)
- The purpose of amendment is not "comprehensiveness" but "variability"
- The goal is "a structure where modification is not painful"
- Schema version management: current **v0.2**

*This rule is subject to amendment by itself.*
