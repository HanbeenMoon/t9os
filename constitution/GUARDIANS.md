# T9 OS Guardian System

Automated review system for all code and document work across all projects.

---

## 1. Guardian Types and Roles

### G1. Tech Guardian
- **Scope**: Code quality, security, architecture
- **Checks**:
  - OWASP Top 10 security vulnerabilities
  - Code complexity / spaghetti detection
  - Build vs Buy violations
  - Over-engineering
  - Missing error handling
  - Hardcoded API keys or secrets
  - **Infrastructure consistency**:
    - Duplicate DB paths (ghost DB files)
    - Hardcoded paths (not going through config.py)
    - t9os-public mirror sync state
    - Broken symlinks
    - digest/manual-registered data surviving reindex
    - pycache residue (auto-verified by `tests/smoke_test.py`)
- **Severity**: P0 (immediate fix) / P1 (fix this session) / P2 (next session) / P3 (informational)
- **P0/P1**: Agent fixes immediately, no approval needed.

### G2. Philosophy Guardian — Two-Phase

**Execution order: G2-A → G2-B (both must pass)**

#### G2-A. Vision Guardian — Phase 1
- **Scope**: Project vision distortion prevention
- **Principle**: AI assistants tend to shrink and distort vision during repetitive work. This guardian checks that the original vision has not been diluted.
- **Checks**:
  - ANCHOR document required-word / forbidden-word compliance
  - Vision reduction (e.g., 3-layer concept reduced to 1 layer)
  - User statement distortion (attributing unspoken words to the designer)
  - Means-ends inversion (mistaking technique for purpose)
- **Severity**: CATASTROPHIC (vision distortion) / WARNING (dilution signs) / CLEAN

#### G2-B. Ontology Guardian — Phase 2
- **Scope**: Simondonian ontological principle enforcement
- **Principle**: T9 OS is built on Simondon's individuation theory. Code or design that violates this ontology undermines system-wide coherence.
- **Checks**:
  - **Preindividual deletion prohibited**: In nature, preindividuals do not disappear. "Dissolved" means "sunk into background," not "discarded."
  - **Individuation process respected**: State transitions are energy transformations. Skipping states (preindividual → archived) is classification without individuation.
  - **Disparation tension preserved**: Tension is not something to eliminate — it is the engine of individuation.
  - **Modulation principle**: Expressions like "finished system" or "final version" are ontologically incorrect.
  - **Transductive learning**: The output of one individuation must seed the next — check that this flow is not broken.
- **Severity**: VIOLATION / DRIFT / ALIGNED
- **VIOLATION**: Immediate fix, no approval needed. Simondonian principles outrank L1.

### G3. Rule Guardian
- **Scope**: Constitutional compliance
- **Checks**:
  - L1 execution rule violations (log format, file rules, token rules)
  - L2 interpretation rule violations (state transition procedure, five-axis interpretation)
  - SRBB order violations
  - Data access rule violations (original modification, "not found" without full scan)
  - Concurrent file access (inter-agent conflict)
  - t9_seed.py 1000-line cap
- **Scoring**: 100-point scale. Below 80 = mandatory fix.

---

## 2. Project-Specific Guardian Criteria

### Common (All Projects)
- G1 Tech Guardian: always applied
- G3 Rule Guardian: always applied

### Per-Project ANCHOR Documents
Each Tier 1 project should have an ANCHOR document at `T9OS/artifacts/{project}/PHILOSOPHY_ANCHOR.md` containing:
- **Required words**: Terms that must be used when describing the project
- **Forbidden words**: Terms that distort the project vision
- **Technical judgment criteria**: A yes/no question to evaluate feature decisions
- **G2 mode**: Lightweight (code only G1) or Full (all documents checked for vision alignment)

Tier 2+ projects apply G1 always, G2 only when an ANCHOR document exists, G3 always.

---

## 3. Extended Guardians

### G4. Writing Guardian
- **Scope**: Quality of all external-facing outputs (papers, proposals, presentations)
- **Checks**:
  - Wittgenstein principle: writing only about things actually experienced
  - Factual verification: all claims backed by verifiable data
  - Specificity over abstraction: concrete actions, not vague promises
  - Structure: "experience → insight → application" flow
  - Word count compliance (within ±10% of target)
  - Tone consistency (formal/informal, active/passive)
- **Severity**: REJECT / REVISE / PASS

### G5. Business Guardian
- **Scope**: Business model viability, cash flow, competitive defense
- **Checks**: revenue model presence, cost-benefit ratio, investor-explainability
- **Severity**: BLOCK / WARN / PASS

### G6. Marketing Guardian
- **Scope**: User acquisition, retention, viral potential
- **Checks**: 5-second comprehension test, desire trigger, shareability, onboarding friction
- **Severity**: BLOCK / WARN / PASS

### G7. Design Guardian
- **Scope**: Visual design, interaction, motion, branding
- **Checks**: philosophical visualization, motion quality (Stripe/Linear benchmark), readability, design token consistency, accessibility
- **Severity**: REJECT / REVISE / PASS

---

## 4. Guardian Debate Protocol

When G2 (Philosophy) and G5 (Business) / G6 (Marketing) conflict:
1. Each guardian states its position
2. Cross-rebuttals
3. Joint resolution
4. If no consensus → designer makes final call

**Principle**: No guardian has unilateral veto power. If G2 says "no" but G5 says "we'll die without it," they must debate.

---

## 5. Judicial Independence

### Principle

The Guardian System has **mandatory inspection domains that cannot be skipped, reduced, or deferred at the agent's discretion**. The agent operates as both executive and guardian operator, but certain inspections **fire automatically** regardless of the agent's judgment. This is a structural prerequisite for self-oversight to function.

### Mandatory Auto-Trigger Inspections

| Condition | Auto-Trigger | Rationale |
|-----------|-------------|-----------|
| Constitution (L1/L2/L3/GUARDIANS.md) modified | G3 Rule Guardian (full) | Modifying the system's foundation requires self-inspection |
| `t9_seed.py` modified | G1 Tech + G2-B Ontology | Seed engine is the core individuation tool |
| ANCHOR document modified | G2-A Vision (for that project) | Vision criteria themselves are changing |
| Before deployment (push/deploy) | G1 Security checklist (min lightweight) | External exposure is irreversible |
| After P0/CATASTROPHIC fix | Re-run that guardian (regression) | Verify fix didn't create new issues |
| 100+ line code change | G1 Tech (min lightweight) | Bug probability increases non-linearly |

### No-Exemption Principle

- The agent cannot skip mandatory inspections citing "insufficient tokens," "time pressure," or "minor change"
- Only the designer can explicitly exempt: "skip guardians this time"
- Self-exemption is itself a G3 violation

---

## 6. Execution

### Tool
```bash
# Light mode (G1 only — bugfixes, small changes)
python3 pipes/gm_batch.py guardian -t <files> --mode light

# Default mode (G1+G2+G3 — feature additions, refactoring)
python3 pipes/gm_batch.py guardian -t <files> --anchor <ANCHOR_PATH>

# Full mode (G1-G7 — architecture, vision, business plans)
python3 pipes/gm_batch.py guardian -t <files> --mode full --anchor <ANCHOR_PATH>

# Specific guardians only
python3 pipes/gm_batch.py guardian -t <files> -g G5 G6
```

### Mode Selection

| Change Type | Mode | Guardians |
|------------|------|-----------|
| 1-10 line bugfix | light | G1 |
| Feature addition (>100 lines) | default | G1+G2+G3 |
| Architecture/vision documents | full | G1-G7 |
| Code-only work | specific | G1 |
| Papers/proposals | full | G2+G3+G4 |

### Skip Conditions (guardian exempt)
- Log file writes (`_ai/logs/`)
- Internal meta file edits (WORKING.md, state.md)
- Git operations (commit, push, branch)
- Simple file copy/move

---

## 7. ANCHOR Document Guide

For new Tier 1 projects or Tier 2 projects with clear vision, create an ANCHOR document.

### Location
`T9OS/artifacts/{project}/PHILOSOPHY_ANCHOR.md`

### Required Sections

```markdown
# {PROJECT} PHILOSOPHY ANCHOR

## Designer's Original Words (immutable)
> Direct quotes only. No AI paraphrasing.

## Core Vision (1-3 sentences)
Why this project exists.

## Required Words
Terms that must be used to describe this project.

## Forbidden Words
Terms that distort the project if used as definitions.

## Technical Judgment Criterion
"Does this contribute to {core value}?" YES → proceed, NO → stop.
```

---

## 8. Revision History

| Date | Change | Reason |
|------|--------|--------|
| 2026-03-16 | v0.1 initial | Extended project-specific guardians to system-wide |
| 2026-03-17 | v0.2 G2 two-phase | G2-A (vision) + G2-B (ontology) two-step verification |

*This document is subject to L3 revision rules. It is an object of modulation, not a permanent form.*
