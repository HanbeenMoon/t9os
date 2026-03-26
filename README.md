# T9 OS

[![License](https://img.shields.io/github/license/HanbeenMoon/t9os)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![Status](https://img.shields.io/badge/status-active%20development-brightgreen)]()
[![Last Commit](https://img.shields.io/github/last-commit/HanbeenMoon/t9os)](https://github.com/HanbeenMoon/t9os/commits/main)
[![Philosophy](https://img.shields.io/badge/philosophy-Simondon-purple)]()

A personal operating system built on top of Claude Code, grounded in Gilbert Simondon's philosophy of individuation.

T9 OS turns an AI coding assistant into a full life-and-work orchestration layer. It manages tasks, decisions, projects, and knowledge — not through rigid categories, but through a state machine modeled on how things actually come into being.

[![demo](https://asciinema.org/a/3oAJ2fpx5B5Yf9No.svg)](https://asciinema.org/a/3oAJ2fpx5B5Yf9No)

Built by a non-developer using philosophical intuition and AI pair programming. This is not production software. It is one person's answer to the question: *what if your operating system understood that ideas start as tension, not as tickets?*

---

## Why?

Most productivity tools treat ideas as static items. You create a task, it sits in a list, you check it off. But that is not how thinking actually works. Ideas emerge from tension between incompatible things — a deadline pulling one way, a creative urge pulling another. The interesting stuff happens in the collision.

T9 OS is built around that observation. Instead of "todo → done," it tracks how things come into being: a vague impulse becomes a tension, the tension produces a candidate, the candidate gets worked on, and eventually it stabilizes — or dissolves back into the background. Nothing gets deleted. Everything leaves a trace.

The philosophy (Simondon) gives this a rigorous foundation, but you don't need to read Simondon to use or understand the system. The core idea is simple: **treat your workflow like a living process, not a filing cabinet.**

---

## Quick Look

Here is how an entity moves through the system — say, an idea for a new feature:

```
1. You mention "maybe we should add calendar sync" in passing
   → t9_seed captures it as a preindividual entity

2. The system notices it conflicts with an existing deadline
   → state becomes tension_detected

3. You say "let's do it" — the system generates a plan
   → state becomes candidate_generated

4. Work begins
   → state becomes individuating

5. Calendar sync ships
   → state becomes stabilized

6. Months later, it's superseded by a better approach
   → state becomes dissolved (sinks into sediment, never deleted)
```

Each transition is logged. The system knows *why* things changed, not just *that* they changed.

---

## What it does

T9 OS sits between a human operator ("the designer") and multiple AI agents (Claude Code, Codex, Gemini). The human sets direction. The system handles execution, judgment, and verification autonomously.

Core capabilities:

- **Entity lifecycle management** — everything (tasks, ideas, impulses, documents) is an "entity" tracked through a 12-state Simondonian state machine
- **3-tier constitution** — L1 (execution rules), L2 (interpretation/transition logic), L3 (self-amendment rules). The system can rewrite its own rules through a defined process
- **PreToolUse policy hooks** — hard gates (bash-level blocks on dangerous commands) and soft gates (LLM-based judgment on philosophy alignment, build-vs-buy decisions)
- **Guardian system** — 7 AI reviewers that check every significant output: tech quality, philosophical alignment (2-stage), rule compliance, reproducibility, UX, and integration
- **MCP server** — the seed engine exposed as a Model Context Protocol server, so Claude Code calls it as a native tool rather than shelling out
- **Multi-agent orchestration** — cc (Claude Code) as control tower, cx (Codex) for bulk code generation, gm (Gemini) for OCR and batch work
- **Architecture Decision Records** — 61 ADRs documenting every significant design choice, each mapped to a Simondonian phase

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   CLAUDE.md                      │
│            (top-level system prompt)              │
├─────────────────────────────────────────────────┤
│                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ constitution │  │    telos     │  │ decisions│ │
│  │ L1 L2 L3    │  │ MISSION     │  │ 61 ADRs  │ │
│  │ GUARDIANS   │  │ SIMONDON    │  │          │ │
│  └──────┬──────┘  │ GOALS       │  └──────────┘ │
│         │         │ MODELS      │                 │
│         ▼         └─────────────┘                 │
│  ┌─────────────┐                                  │
│  │  t9_seed.py  │ ← seed engine (~900 lines)     │
│  │  SQLite FTS  │                                 │
│  └──────┬──────┘                                  │
│         │                                         │
│    ┌────┴────┐                                    │
│    │   lib/  │ config, logger, parsers,           │
│    │         │ transduction, ipc, export           │
│    └────┬────┘                                    │
│         │                                         │
│    ┌────┴─────────────────────┐                   │
│    │         pipes/           │                    │
│    │  gm_batch    (guardian)  │                    │
│    │  t9_auto     (concepts) │                    │
│    │  ceo_brief   (telegram) │                    │
│    │  deadline    (notify)   │                    │
│    │  calendar    (sync)     │                    │
│    │  healthcheck (status)   │                    │
│    │  pipeline_composer      │                    │
│    │  session_lock           │                    │
│    └──────────────────────────┘                   │
│                                                   │
│  ┌──────────┐  ┌──────────────────┐              │
│  │  mcp/    │  │  .claude/hooks/  │              │
│  │  server  │  │  hard-gate.sh    │              │
│  └──────────┘  │  soft-gate.md    │              │
│                │  session-*.sh    │              │
│                └──────────────────┘              │
└─────────────────────────────────────────────────┘

Entity lifecycle (Simondonian state machine):

  preindividual → tension_detected → candidate_generated → individuating
       → stabilized → archived
                    → suspended → reactivated
                    → split / merged (→ re-individuation)
                    → dissolved (→ sediment)
```

---

## Philosophy

T9 OS is built on Gilbert Simondon's theory of individuation (1958). The core claim: individuals (tasks, ideas, projects) don't exist first and then get organized. They *come into being* through a process — and the process is what matters.

Key Simondonian concepts mapped to the system:

| Concept | In Simondon | In T9 OS |
|---------|-------------|----------|
| **Preindividual** | Supersaturated potential before individuation | `field/inbox/` — raw ideas, impulses, tensions |
| **Metastability** | Unstable equilibrium loaded with potential | `tension_detected` — something wants to become something |
| **Disparation** | Tension between incompatible dimensions | "research deadline vs startup urge" — the engine of change |
| **Transduction** | Structure propagating across domains | Pattern from one project becoming principle in another |
| **Concretization** | Abstract→concrete evolution of technical objects | Tool integration maturity (measured on 4-level scale) |
| **Associated milieu** | Feedback loop between object and environment | Filesystem + APIs + human intent = living context |
| **Modulation** | Continuous, permanently variable self-formation | L3 self-amendment — the system is never "done" |

The practical consequence: nothing gets deleted. `dissolved` means "sank into the background" — like sediment. The system tracks 12 states, not because complexity is a goal, but because that is how things actually move through a person's life.

---

## What's interesting here

A few things that might be worth looking at if you build AI-augmented workflows:

**Policy hooks as a governance layer.** `pre-tool-hard-gate.sh` intercepts every tool call Claude Code makes and blocks dangerous operations (force push, `rm -rf`, credential access). This was implemented before Anthropic shipped official hook support — the pattern turned out to be the same one they chose.

**The MCP server pattern.** `mcp/t9_seed_server.py` wraps the seed engine as a Model Context Protocol server. Claude Code calls `t9_capture`, `t9_search`, `t9_status` as native tools instead of running bash commands. Also implemented before Anthropic's official MCP integration.

**Constitution as code.** The 3-tier constitution isn't documentation — it's the actual operating logic. L1 defines what entities are and how they move. L2 defines when transitions happen (using disparation as the trigger model). L3 defines how L1 and L2 can be changed. The Guardian system enforces all of it.

**Philosophical consistency as a real constraint.** The Guardian system includes two philosophy reviewers (G2-A: vision alignment, G2-B: ontological alignment). Code that violates Simondonian principles gets flagged the same way code with security vulnerabilities does. This sounds excessive until you realize that without it, AI assistants quietly simplify your ideas into something more conventional.

---

## Structure

```
T9OS/
├── t9_seed.py           # seed engine — entity management, search, lifecycle
├── constitution/        # L1 (execution), L2 (interpretation), L3 (amendment), Guardians
├── telos/               # mission, goals, Simondon mapping, mental models
├── docs/decisions/           # 66 Architecture Decision Records
├── lib/                 # config, logger, parsers, transduction, IPC
├── pipes/               # pipelines — guardian batch, CEO brief, calendar, deadlines
├── mcp/                 # MCP server wrapping t9_seed.py
├── artifacts/           # generated documents, research, whitepapers
├── deploy/              # deployment configs
├── data/                # runtime data (conversations, composes) [gitignored]
├── field/               # preindividual entities (inbox, impulses) [gitignored]
├── spaces/              # active/suspended/archived entities [gitignored]
└── memory/              # long-term memory store
```

---

## Install

```bash
pip install git+https://github.com/HanbeenMoon/t9os.git
```

### First run

```bash
$ t9 init --quick

  === T9 OS v0.3.0 -- Initialization ===

  Config: ~/.config/t9os
  Data:   ~/.t9os_data
  Template: constitution/L1_execution.md
  Template: constitution/L2_interpretation.md
  Template: constitution/L3_amendment.md
  Template: telos/MISSION.md
  Config:  config.toml
  DB:     ~/.t9os_data/.t9.db (0 entities)

  T9 OS initialized. Run 't9 daily' for your daily brief.
```

### Core commands (no API keys required)

```bash
t9 capture "an idea, a tension, anything"   # save a preindividual
t9 status                                   # system overview
t9 daily                                    # morning briefing
t9 search "query"                           # full-text search
t9 transition <id> stabilized               # move entity state
t9 reindex                                  # rebuild index
```

### Optional integrations

| Feature | What you need | Install |
|---------|--------------|---------|
| Telegram alerts | Bot token from @BotFather | `pip install "t9os[telegram]"` |
| Google Calendar sync | OAuth credentials | `pip install "t9os[calendar]"` |
| Gemini batch ops | API key | `pip install "t9os[gemini]"` |
| Everything | All of the above | `pip install "t9os[all]"` |

Core features (capture, search, daily, transitions) work entirely offline with zero API keys.

### For reading, not running

If you just want to study the design:

1. **Constitution** — `src/t9os/templates/constitution/` — self-amending 3-tier rule system
2. **ADRs** — `docs/decisions/` — 61 architectural decisions with Simondonian phase metadata
3. **Seed engine** — `src/t9os/engine/seed.py` — entity lifecycle with SQLite FTS

---

## Built with

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — primary AI agent
- Python 3 + SQLite (FTS5) — seed engine
- Bash — policy hooks, cron orchestration
- Gemini CLI — batch operations, OCR
- Simondon's *L'individuation à la lumière des notions de forme et d'information* (1958) — philosophical foundation

---

## License

Not yet decided. The code is being shared for transparency and as a reference architecture. If you find something useful, take it.

---

*T9 OS is a metastable system. It is not finished. By design, it never will be.*
