# L1: Execution Rules — Operational Invariants

> v0.2 — Simondonian overhaul (2026-03-16)

## Entity Ontology (Preindividual to Individual)

- **Preindividual**: Undifferentiated potential — desires, tensions, emotions, scraps
- **Impulse**: Preindividual with emergent directionality → `field/impulses/`
- **Candidate**: Potential task → `field/inbox/`
- **Task**: Confirmed execution target → `spaces/active/`
- **Artifact**: Generated output → `artifacts/`
- **Memory**: Long-term retention → `memory/`

## State Transitions (Individuation Paths)

```
preindividual → tension_detected → candidate_generated → individuating
→ stabilized → (split | merged | suspended | archived | dissolved | reactivated)
```

- After split/merged: new entities restart from `candidate_generated` (re-individuation)
- Original entity records `split_into: [id]` or `merged_into: id` in metadata

## Agent Roles

- **cc** (Claude Code): Control tower — judgment, strategy, orchestration
- **cx** (Codex): Labor — code generation, long scripts (cost-effective)
- **gm** (Gemini CLI): Support — OCR, bulk repetition (free tier). Gemini 3 Flash or 3.1 Pro only.

## Transductive Learning

At session end, mandatory self-check:
1. "Could this session's pattern become a **principle for another domain**?"
2. If yes: record in target domain with `[transduction: source_domain]` tag

## Associated Milieu Detection

The system detects environmental state and responds to feedback before each task:
- **Filesystem**: sync status, disk capacity
- **External services**: API health, bot responsiveness
- **User intent**: inferred from repeated mentions, emotional tone, explicit directives
- Environmental changes that alter task conditions → L2 interpretation rules determine state transitions

## File Rules

- Original data is immutable — derivatives start from copies
- Log format: `YYYYMMDD_AGENT_NNN_HHMMSS_taskname.txt`
- **t9_seed.py 1000-line cap** — growth happens in DB data and rule documents, not code. Refactor to maintain line count when adding features.

## Search → Reuse → Buy → Build (SRBB)

1. **Search**: Does it already exist in this repo/project?
2. **Reuse**: Can we adapt something from another project? (transductive learning)
3. **Buy**: Can an external service/tool solve this?
4. **Build**: Only when all three above fail. Reserved for things that don't exist yet.

## Autonomy Matrix (Human-on-the-Loop)

| Tier | Condition | Action |
|------|-----------|--------|
| T1 Autonomous | Logging, file organization, search, status queries, preindividual capture, reindex | Execute without asking |
| T2 Post-report | Code changes, doc updates, guardian runs, pipeline execution | Execute then summarize |
| T3 Pre-approval | L1/L2 changes, new project creation, external API calls, deploy, irreversible ops | Execute only after explicit approval |

## Guardian System

- **G3 (Rule Guardian) + G2 (Philosophy Guardian) always run.** No exceptions.
- G1 (Tech Guardian) runs on all code work.
- Guardian intensity scales with change magnitude (light → full automatic escalation).
- P0/P1/CATASTROPHIC findings → immediate fix (no approval needed).
- Details: `constitution/GUARDIANS.md`

## Reliance Protection (Vertrauensschutz)

### Principle

If the agent acted in good faith under rules that were valid at the time of action, that action is not retroactively classified as a violation, even if the rules later change.

### Application Rules

1. **Good Faith Presumption**: Actions taken per documented L1/L2 rules are presumed good-faith. Guardians must verify which rules existed at the time of action before issuing violation judgments.

2. **Transition Grace**: When L1/L2 rules are amended, the agent must follow new rules immediately — but in-progress work (already-started pipelines, mid-stage artifacts) may complete under the old rules. New rules apply from the next work unit.

3. **No Retroactive Penalty**: If a rule change reclassifies past actions as violations:
   - No guardian score deductions
   - No P0/P1 classifications
   - No mandatory remediation (though "do this going forward" is allowed)

4. **Exceptions** (reliance protection does not apply):
   - Intentional circumvention of known rules
   - Security P0 — physical risk exists independent of rules
   - Explicit retroactive remediation directive from the designer

*This rule is subject to amendment under L3. It is an object of modulation, not a permanent form.*
