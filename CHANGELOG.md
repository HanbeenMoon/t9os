# Changelog

All notable changes to T9 OS will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.3.0] - 2026-03-26

### Added
- `pip install t9os` support with `pyproject.toml` (hatchling build)
- Typer CLI: `t9` command with 24 subcommands
- `t9 init` wizard for first-time setup (creates XDG dirs, copies templates, initializes DB)
- XDG-based config (`~/.config/t9os/`) and data (`~/.t9os_data/`) directories
- `config.toml` support for persistent configuration
- `src/t9os/` package layout with `engine/`, `lib/`, `pipes/`, `templates/`
- Dockerfile for containerized deployment
- `--version` flag

### Changed
- Restructured from flat layout to `src/` layout (PEP 517/518 compliant)
- All imports updated from `lib.X` to `t9os.lib.X`
- Config paths no longer hardcoded; uses environment variables or XDG defaults
- Engine versioned to v0.3

### Removed
- Root-level `t9_seed.py`, `t9_viz.py`, `lib/`, `pipes/`, `constitution/`, `telos/`
  (all moved into `src/t9os/`)

## [2.1.0] - 2026-03-26

### Changed
- Full English localization of all documentation, ADRs, and code comments
- ADR set curated to 47 architecture-relevant decisions (removed personal/project-specific ADRs)
- README rewritten with Quick Start section and updated metrics

## [2.0.0] - 2026-03-23

### Added
- Three-tier constitution (L1 execution, L2 interpretation, L3 amendment)
- Guardian system with 7 specialized AI reviewers (G1-G7)
- Legal theory integration (non-retroactivity, judicial independence, reliance protection)
- PreToolUse policy hooks enforcing hard safety gates
- Orient Layer Architecture (OLA) for structured soft gates
- MCP server for seed engine (t9_seed_server.py)
- Multi-session IPC with file locking
- 47 Architecture Decision Records
- Telegram bot with voice transcription pipeline
- Gemini batch processing for guardian reviews
- Simondon state machine with 12 entity states
- Session live-read from JSONL (no conversion wait)

### Changed
- Seed engine rewritten with full-text search (SQLite FTS5)
- Migrated from Notion to local SQLite
- Migrated from PowerShell to Python
- Bare `except` clauses replaced with `except Exception`

## [1.0.0] - 2026-02-01

### Added
- Initial T9 OS with basic entity management
- Notion-based storage
- PowerShell Telegram agent
