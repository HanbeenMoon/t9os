# Changelog

All notable changes to T9 OS will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.3.0] - 2026-03-26

### Added
- **pip install support** — `pip install git+https://github.com/HanbeenMoon/t9os.git`
- **Typer CLI** with 24 commands, auto-completion, `--help` for everything
- **`t9 init --quick`** — interactive setup wizard, creates config + data dirs + DB
- **src/ layout** — proper Python package structure (`src/t9os/`)
- **pyproject.toml** with hatchling build, optional extras (`[telegram]`, `[calendar]`, `[gemini]`)
- **XDG config** — `~/.config/t9os/` for settings, `~/.t9os_data/` for data
- **Template system** — default constitution and telos shipped with package, copied on init
- **Dockerfile** for containerized deployment
- **Environment variable overrides** — `T9OS_CONFIG_DIR`, `T9OS_DATA_DIR`, `T9OS_DB_PATH`

### Changed
- All imports refactored from `lib.X` to `t9os.lib.X`
- Config paths are now XDG-compliant (no more hardcoded paths)
- Core commands work with zero API keys (capture, search, daily, transitions)
- All documentation and code comments in English

### Removed
- Personal/project-specific ADRs (SSK, ODNAR, SC41, etc.)
- Internal design documents (BIBLE.md, V2 research synthesis)
- Korean language from all files

## [2.0.0] - 2026-03-23

### Added
- Three-tier constitution (L1 execution, L2 interpretation, L3 amendment)
- Guardian system with 7 specialized AI reviewers (G1-G7)
- Legal theory integration (non-retroactivity, judicial independence, reliance protection)
- PreToolUse policy hooks enforcing hard safety gates
- MCP server for seed engine (t9_seed_server.py)
- Multi-session IPC with file locking
- 62 Architecture Decision Records
- Telegram bot with voice transcription pipeline
- Gemini batch processing for guardian reviews
- Simondon state machine with 12 entity states

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
