# T9 OS — AI Operating System

[![Python](https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-FTS5-003B57?logo=sqlite&logoColor=white)]()
[![Claude Code](https://img.shields.io/badge/Claude_Code-Anthropic-8A2BE2)]()
[![License](https://img.shields.io/github/license/HanbeenMoon/t9os)](LICENSE)
[![ADRs](https://img.shields.io/badge/ADRs-68_decisions-orange)]()
[![Status](https://img.shields.io/badge/status-production-brightgreen)]()

**One person. 18 production pipelines. A complete AI orchestration layer — built solo over three months using Claude Code and philosophical intuition.**

Not theoretical. Production-grade.

---

## Overview

T9 OS is a personal operating system layered on top of Claude Code. It replaces the conventional productivity stack — todos, project managers, note apps — with a single, self-governing AI orchestration layer.

Everything passes through a 12-state lifecycle engine modeled on Gilbert Simondon's theory of individuation. A raw idea enters as `preindividual`. It becomes `tension_detected` when it conflicts with something else. It moves through `candidate_generated → individuating → stabilized`. Nothing is ever deleted — dissolved entities sink into sediment and remain searchable.

The result: **1,104 entities tracked**, **68 architectural decisions logged**, **18 pipelines running in production**, **8 scheduled cron jobs** — all operated by a single human who sets direction while the system handles execution, judgment, and verification autonomously.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  CLAUDE.md — top-level system constitution               │
│                                                          │
│  ┌─────────────────┐   ┌──────────────┐  ┌───────────┐ │
│  │ constitution/   │   │ telos/       │  │decisions/ │ │
│  │ L1 hard rules   │   │ MISSION      │  │ 68 ADRs   │ │
│  │ L2 transitions  │   │ GOALS        │  │           │ │
│  │ L3 self-amend   │   │ SIMONDON     │  └───────────┘ │
│  │ 7 Guardians     │   └──────────────┘                │
│  └────────┬────────┘                                    │
│           │                                             │
│    ┌──────▼──────┐                                      │
│    │ t9_seed.py  │  seed engine — ~900 lines            │
│    │ SQLite FTS5 │  entity lifecycle, search, IPC       │
│    └──────┬──────┘                                      │
│           │                                             │
│    ┌──────▼──────────────────────────────┐              │
│    │ pipes/  — 18 production pipelines   │              │
│    │  gm_batch        guardian batch     │              │
│    │  t9_ceo_brief    Telegram briefing  │              │
│    │  calendar_sync   Google Calendar    │              │
│    │  deadline_notify push alerts        │              │
│    │  pipeline_composer  auto-routing    │              │
│    │  session_live_read  JSONL sync      │              │
│    │  healthcheck     system monitoring  │              │
│    │  whisper_pipeline  voice → entity   │              │
│    └─────────────────────────────────────┘              │
│                                                         │
│  ┌──────────────┐   ┌──────────────────────────┐       │
│  │ mcp/         │   │ .claude/hooks/            │       │
│  │ MCP server   │   │ pre-tool-hard-gate.sh     │       │
│  │ native tools │   │ soft-gate LLM policy      │       │
│  └──────────────┘   └──────────────────────────┘       │
└──────────────────────────────────────────────────────────┘

Entity state machine:
  preindividual → tension_detected → candidate_generated
  → individuating → stabilized → archived
                 → suspended → reactivated
                 → split / merged
                 → dissolved (sediment, permanent trace)
```

---

## Key Pipelines

| Pipeline | What it does |
|---|---|
| `t9_seed.py` | Core engine — entity lifecycle, FTS5 search, state transitions (~900 lines) |
| `gm_batch.py` | 7-tier Guardian review system — runs Gemini batch against every significant output |
| `t9_ceo_brief.py` | Daily Telegram briefing — status, urgent items, decisions pending |
| `calendar_sync.py` | Two-way Google Calendar sync — entities with deadlines auto-appear as events |
| `deadline_notify.py` | Push alerts on approaching deadlines via Telegram |
| `pipeline_composer.py` | Classifies and routes raw input to the right pipeline automatically |
| `session_live_read.py` | Reads Claude Code JSONL sessions in real time — no waiting for session end |
| `healthcheck.py` | Full system health check — reports to Telegram if anything breaks |
| `whisper_pipeline.py` | Voice memo → transcription → entity capture |
| `hwp_convert.py` | Korean HWP document → DOCX conversion with original protection |
| `t9_auto.py` | Gemini-powered concept extraction from entities |
| `integrity_check.py` | Cross-checks data consistency across the entity store |
| `adr_auto.py` | Detects significant commits and auto-generates Architecture Decision Records |
| `safe_change.sh` | Snapshot → change → smoke test → rollback safety wrapper |
| `session_lock.py` | Multi-agent session isolation — prevents concurrent writes |
| `gdrive_upload.py` | Google Drive upload for generated documents and exports |
| `migration_verify.py` | Validates schema migrations before applying |
| `cron_runner.sh` | Single cron entrypoint — schedules and logs all 8 timed jobs |

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Agents | Claude Code (control tower), Gemini CLI (batch/OCR), Codex (code generation) |
| Core Engine | Python 3.10+, SQLite with FTS5 full-text search |
| Protocol | Model Context Protocol (MCP) — seed engine exposed as native Claude tools |
| Policy Enforcement | Bash hooks (PreToolUse hard gates) + LLM soft gates |
| Notifications | Telegram Bot API |
| Calendar | Google Calendar API (OAuth 2.0) |
| Voice | OpenAI Whisper |
| Scheduling | cron + custom cron_runner.sh |
| Philosophy | Gilbert Simondon — individuation theory as state machine design |

---

## Live Stats

| Metric | Count |
|---|---|
| Total entities tracked | 1,104 |
| Production pipelines | 18 |
| Scheduled cron jobs | 8 |
| Architecture Decision Records | 68 |
| Entity states | 12 |
| Active transduction relations | 12 |

---

## Demo

> Screenshots coming. The system runs headless — primary interface is Telegram and Claude Code CLI.

**CLI status:**
```
$ python3 t9_seed.py status

=== T9 OS Seed v0.2 (total 1104) ===

  archived              514  ##############################
  stabilized            252  ##############################
  tension_detected      167  ##############################
  preindividual          84  ##############################
  sediment               61  ##############################
  candidate_generated    18  ##################
  suspended               3
  dissolved               3
  individuating           1
  impulse                 1

  transduction relations: 12
```

---

## What Makes This Different

**Policy hooks as governance.** `pre-tool-hard-gate.sh` intercepts every tool call and blocks dangerous operations — force push, `rm -rf`, credential access, HWP originals — before they execute. Hard rules enforced in Bash; soft rules (build-vs-buy, philosophical alignment) enforced by an LLM running inline.

**Constitution as code.** Three tiers: L1 defines immutable execution rules. L2 defines transition logic and interpretation. L3 defines how L1 and L2 can be amended. The system can rewrite its own rules through a governed process. All changes leave ADR traces.

**MCP before MCP was standard.** `mcp/t9_seed_server.py` wraps the seed engine as a Model Context Protocol server — Claude Code calls `t9_capture`, `t9_search`, `t9_status` as native tools. Implemented independently before Anthropic shipped official MCP integration.

**Philosophy as constraint.** Two of the seven Guardians check Simondonian alignment. Code that simplifies ideas into conventional patterns gets flagged the same way security vulnerabilities do. Without this, AI assistants quietly flatten your thinking.

---

## Structure

```
t9os/
├── t9_seed.py           # seed engine — entity management, search, lifecycle
├── constitution/        # L1 / L2 / L3 rules + 7 Guardian definitions
├── telos/               # mission, goals, Simondon mapping
├── decisions/           # 68 Architecture Decision Records
├── lib/                 # config, logger, parsers, transduction, IPC
├── pipes/               # 18 production pipelines
├── mcp/                 # MCP server wrapping t9_seed.py
├── tests/               # smoke tests (37 checks)
└── artifacts/           # generated documents, whitepapers
```

---

## Built by

[Hanbeen Moon](https://github.com/HanbeenMoon) — designer, not a developer. Built this system using Claude Code as a pair programmer over three months. The architecture decisions are documented in `decisions/`. The philosophy is documented in `telos/`. The code does what it says.

---

*T9 OS is a metastable system. Not finished. By design, it never will be.*
