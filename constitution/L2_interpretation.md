# L2: Interpretation Rules — State Transition Criteria

> v0.2 — Simondonian overhaul (2026-03-16)

## Disparation-Based State Transitions

State transitions are not simple "condition met" checks — they occur when **tension between incompatible dimensions** resolves into a new structure. For each transition, identify the three elements of disparation:

| Transition | dimension_a | dimension_b | resolution_dimension |
|------------|------------|------------|---------------------|
| preindividual → tension_detected | Current state (stability) | Desire/discomfort (change) | Naming the tension |
| tension → candidate | Abstract tension | Concrete action possibility | Action candidate generation |
| candidate → individuating | Potential task | Resource/time constraints | Approval or deadline pressure |
| individuating → stabilized | Execution uncertainty | Expected output | 1+ artifact produced |
| stabilized → archived | Inertia (more could be done) | Completion criteria (enough) | Retrospective recorded |

### preindividual → tension_detected
- User expresses discomfort, idea, or desire
- Recurring pattern detected (same topic mentioned 3+ times)
- **Disparation identification required**: "What two things are incompatible?"

### tension_detected → candidate_generated
- Concrete action possibility identified
- Clarity reaches "should we try this?" level

### candidate_generated → individuating
- User approval or explicit directive
- Automatic promotion under deadline pressure

### individuating → stabilized
- 1+ artifact produced / next action clear

### Re-individuation After split/merged
- **split**: original → dissolved, sub-entities restart from `candidate_generated`
- **merged**: originals → dissolved, unified entity restarts from `candidate_generated`
- Re-individuation inherits metadata and learnings from originals

### suspended / dissolved / archived / reactivated
- **suspended**: external blocker or priority drop
- **dissolved**: explicit user cancellation or 30+ days suspended
- **archived**: post-stabilization with retrospective complete
- **reactivated**: related keyword re-emergence or user reactivation

## Five-Axis Interpretation

All input is interpreted along these five axes:
1. **Intent**: create / explore / solve / earn / express / become
2. **State**: exploring / executing / on-hold
3. **Resource**: time, tokens, money, files, people, tools, knowledge
4. **Constraint**: deadline, budget, capacity, skill, access
5. **Artifact**: code, document, design, data

## Preindividual Triage Protocol

When preindividual count exceeds 50, run triage. Not every session — only when backlog accumulates.

### Simondonian Principle
- Preindividuals **resist classification**. Premature categorization kills potential.
- Triage goal is not classification but **tension detection (disparation detection)**.
- Ask not "What is this?" but "Where does this create tension?"

### Three-Phase Protocol

**Phase 1: Scan (30s per item)**
For each preindividual, assess three things only:
- **Has a deadline?** → YES: immediately `tension_detected` + urgency tag
- **Related to existing entity?** → YES: `relate` only, keep as preindividual
- **Neither?** → Leave as-is (preindividuals are allowed to remain preindividual)

**Phase 2: Tension Detection (pattern-based)**
After scan, look for patterns across all preindividuals:
- Same keyword/topic appears 3+ times → `tension_detected` + note why it recurs
- Same project referenced 5+ times → consider `merged` (unify into one candidate)
- 30+ days old → consider `dissolved` (only after designer confirmation)

**Phase 3: Artifact Linking**
For entities where tension was detected:
- Does an artifact already exist? (search `artifacts/`) → if yes, `relate`
- Promote to candidate only when designer approval or deadline pressure exists

### What Triage Does NOT Do
- Sort into project folders (Simondon violation — preindividuals can span multiple projects)
- Force-individuate every preindividual (remaining preindividual is normal)
- Auto-dissolve without confirmation (30-day rule requires designer check)
- Over-tag (3+ tags per item = meta-work)

## Guardian Interpretation Criteria

### Execution Tool
- `gm_batch.py guardian`: batch guardian review using Gemini (free, parallel)
- The control tower serves as guardian chief — reviews results, makes P0 calls, applies fixes

### Mode Selection

| Change Type | Mode | Guardians | CLI |
|------------|------|-----------|-----|
| 1-10 line bugfix | light | G1 | `--mode light` |
| Feature addition (>100 lines) | default | G1+G2+G3 | (default) |
| Architecture/vision documents | full | G1-G7 | `--mode full` |

### Judgment Interpretation
- "Vision distortion": ANCHOR forbidden-word 1x = WARNING, all required-words missing = CATASTROPHIC
- Light → heavy escalation: automatic on P0 discovery in G1
- New project creation: check for ANCHOR document. If absent, skip G2.

### Reproducibility Rule (non-negotiable)
- **New pipeline/tool creation**: update CLAUDE.md pipeline table + L1 + memory simultaneously
- **Unrecorded = nonexistent.** If another session cannot find it, it does not exist.

*This rule is subject to amendment under L3. Interpretation itself is an object of modulation.*
