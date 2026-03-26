# AI Session Manager

Read and search [Claude Code](https://docs.anthropic.com/en/docs/claude-code) JSONL conversation sessions in real time -- without waiting for session end.

## What it does

- **List** recent sessions with message counts and timestamps
- **Read** a specific session by ID prefix
- **Search** across all sessions by keyword (case-insensitive)
- **Export** sessions as Markdown files for archival

Claude Code writes conversation data to disk as JSONL files during the session. This tool reads those files directly, so you can inspect active and past conversations from any terminal.

## Requirements

- Python 3.10+
- No external dependencies (stdlib only)
- Claude Code must be installed (the tool reads its JSONL output)

## Installation

Copy `skill.py` anywhere on your machine. No `pip install` needed.

```bash
# Option A: run directly
python3 skill.py

# Option B: symlink for convenience
ln -s /path/to/skill.py ~/.local/bin/session-manager
```

## Usage

```bash
# List the 10 most recent sessions
python3 skill.py

# List the 20 most recent sessions
python3 skill.py --recent 20

# Read a specific session (use first 8 chars of session ID)
python3 skill.py --session 636a72df

# Full conversation dump
python3 skill.py --session 636a72df --full

# Search for a keyword across last 50 sessions
python3 skill.py --search "deploy"

# Export all sessions as Markdown
python3 skill.py --sync
```

## Configuration

The tool auto-detects Claude Code's JSONL directory based on your working directory. Override with environment variables if needed:

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_JSONL_DIR` | `~/.claude/projects/<cwd-slug>/` | Directory containing `.jsonl` files |
| `SESSION_EXPORT_DIR` | `./session-exports/` | Output directory for `--sync` exports |

## How it works

1. Claude Code writes each conversation turn as a JSON line in `~/.claude/projects/<slug>/<session-id>.jsonl`
2. This tool reads those files, filters for `user` (external) and `assistant` messages, and extracts the text content
3. Search scans all message text with simple substring matching
4. Export writes one Markdown file per session with `[User]` / `[Assistant]` headers

## Integration with Claude Code

You can use this as a Claude Code skill by referencing it in your `CLAUDE.md`:

```markdown
## Session search
Run `python3 /path/to/skill.py --search "keyword"` to find past conversations.
```
