# T9 OS — AI Operating System

[![Python](https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-FTS5-003B57?logo=sqlite&logoColor=white)]()
[![Claude Code](https://img.shields.io/badge/Claude_Code-Anthropic-8A2BE2)]()
[![License](https://img.shields.io/github/license/HanbeenMoon/t9os)](LICENSE)
[![ADRs](https://img.shields.io/badge/ADRs-47_decisions-orange)]()
[![Status](https://img.shields.io/badge/status-production-brightgreen)]()

**One person. 18 production pipelines. A complete AI orchestration layer — built solo over three months using Claude Code and philosophical intuition.**

Not theoretical. Production-grade.

---

## Overview

T9 OS is a personal operating system layered on top of Claude Code. It replaces the conventional productivity stack — todos, project managers, note apps — with a single, self-governing AI orchestration layer.

Everything passes through a 12-state lifecycle engine modeled on Gilbert Simondon's theory of individuation. A raw idea enters as `preindividual`. It becomes `tension_detected` when it conflicts with something else. It moves through `candidate_generated → individuating → stabilized`. Nothing is ever deleted — dissolved entities sink into sediment and remain searchable.

### What it looks like in practice

```
$ t9 daily

  === T9 OS Seed v0.3.0 — Thursday ===

  [!] Deadlines:
    D-3    Client proposal draft
    D-7    Conference submission
    D-14   Product launch

  Active: 142 entities
  Preindividual: 89 | Tension: 31 | Candidate: 12
  Sediment: 24 — dormant entities, searchable via `t9 search`

  [Transduction] Patterns detected:
    [42] API design research → transferable to [78] SDK architecture
    [51] User interview notes → transferable to [90] Onboarding flow
```

```
$ t9 capture "embedding models might be the key — fine-tune on private data, not just API calls"

  Saved: 20260326_embedding_models_might_be_the_key_fi_143022.md
  Concepts: explore, create
  [Transduction] Similar entities found:
    [42] vector search architecture (similarity=1.0, shared=explore)
```

---

## Quick Start

```bash
# Install
pip install git+https://github.com/HanbeenMoon/t9os.git

# Initialize (creates ~/.config/t9os/ and ~/.t9os_data/)
t9 init --quick

# Start using it
t9 capture "my first idea"    # Save a preindividual
t9 status                     # Full system overview
t9 daily                      # Morning briefing
t9 search "query"             # Full-text search
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  constitution/  — governance layer                       │
│  ┌─────────────────┐   ┌──────────────┐  ┌───────────┐ │
│  │ L1 hard rules   │   │ telos/       │  │decisions/ │ │
│  │ L2 transitions  │   │ MISSION      │  │ 47 ADRs   │ │
│  │ L3 self-amend   │   │ SIMONDON     │  │           │ │
│  │ 7 Guardians     │   └──────────────┘  └───────────┘ │
│  └────────┬────────┘                                    │
│           │                                             │
│    ┌──────▼──────┐                                      │
│    │ engine/     │  seed engine — entity lifecycle       │
│    │ seed.py     │  SQLite FTS5 search, IPC              │
│    │ states.py   │  12-state machine                     │
│    └──────┬──────┘                                      │
│           │                                             │
│    ┌──────▼──────────────────────────────┐              │
│    │ pipes/  — 18 production pipelines   │              │
│    │  guardian batch    Telegram brief   │              │
│    │  calendar sync    deadline alerts  │              │
│    │  healthcheck      voice capture    │              │
│    │  auto-routing     session sync     │              │
│    └─────────────────────────────────────┘              │
│                                                         │
│  ┌──────────────┐   ┌──────────────────────────┐       │
│  │ mcp/         │   │ hooks/                    │       │
│  │ MCP server   │   │ hard gates (bash)         │       │
│  │ native tools │   │ soft gates (LLM policy)   │       │
│  └──────────────┘   └──────────────────────────┘       │
└──────────────────────────────────────────────────────────┘

Entity lifecycle:
  preindividual → tension_detected → candidate_generated
  → individuating → stabilized → archived
               → suspended → reactivated
               → split / merged
               → dissolved (sediment — permanent, searchable)
```

---

## Key Pipelines

| Pipeline | What it does |
|---|---|
| `engine/seed.py` | Core engine — entity lifecycle, FTS5 search, state transitions |
| `pipes/gm_batch.py` | 7-tier Guardian review — Gemini batch against significant outputs |
| `pipes/telegram_bot.py` | Telegram briefing — status, urgent items, file receiving |
| `pipes/calendar_sync.py` | Two-way Google Calendar sync |
| `pipes/deadline_notify.py` | Push alerts on approaching deadlines |
| `pipes/pipeline_composer.py` | Classifies and routes raw input automatically |
| `pipes/session_live_read.py` | Reads Claude Code JSONL sessions in real time |
| `pipes/healthcheck.py` | Full system health check with Telegram alerts |
| `pipes/whisper_pipeline.py` | Voice memo → transcription → entity capture |
| `pipes/safe_change.sh` | Snapshot → change → smoke test → rollback wrapper |

---

## What Makes This Different

**Policy hooks as governance.** Hard gates intercept every tool call and block dangerous operations — force push, `rm -rf`, credential access — before they execute. Soft gates run an LLM inline for build-vs-buy decisions and philosophical alignment checks.

**Constitution as code.** Three tiers: L1 defines immutable execution rules. L2 defines transition logic. L3 defines how L1 and L2 can be amended. The system can rewrite its own rules through a governed process. All changes leave ADR traces.

**MCP integration.** The seed engine is exposed as a Model Context Protocol server — Claude Code calls `t9_capture`, `t9_search`, `t9_status` as native tools.

**Philosophy as constraint.** Two of seven Guardians check Simondonian alignment. Code that simplifies ideas into conventional patterns gets flagged the same way security vulnerabilities do.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Agents | Claude Code (orchestration), Gemini (batch/OCR), Codex (generation) |
| Core Engine | Python 3.10+, SQLite FTS5 |
| Protocol | Model Context Protocol (MCP) |
| Policy | Bash hard gates + LLM soft gates |
| Notifications | Telegram Bot API |
| Calendar | Google Calendar API (OAuth 2.0) |
| Voice | OpenAI Whisper |
| Philosophy | Gilbert Simondon — individuation theory as state machine |

---

## Structure

```
t9os/
├── src/t9os/
│   ├── cli.py           # Typer CLI — 24 commands
│   ├── engine/          # seed engine + 12-state machine
│   ├── lib/             # config, parsers, IPC, transduction
│   ├── pipes/           # production pipelines
│   └── templates/       # default constitution + config
├── decisions/           # 47 Architecture Decision Records
├── demos/               # standalone demo projects
├── tests/               # smoke tests
├── docs/                # guides
├── pyproject.toml       # pip install ready
└── Dockerfile           # containerized deployment
```

---

## Built by

[Hanbeen Moon](https://github.com/HanbeenMoon) — designer, not a developer. Built this system using Claude Code as a pair programmer over three months. The architecture decisions are documented in `decisions/`. The philosophy is documented in `telos/`. The code does what it says.

---

*T9 OS is a metastable system. Not finished. By design, it never will be.*
