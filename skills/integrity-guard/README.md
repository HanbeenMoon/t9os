# Integrity Guard

A generic codebase and data integrity checker. Validates file existence, SQLite database health, pipeline freshness, required content, cron jobs, and systemd units -- all from a single configurable tool.

## What it does

| Check | Description |
|-------|-------------|
| **Required files** | Verifies expected files exist at specified paths |
| **Required directories** | Verifies expected directories exist |
| **Pipeline status** | Checks script existence and flags stale files (older than N days) |
| **Database health** | Validates SQLite: file exists, expected tables present, row counts |
| **Required content** | Scans files for required strings (e.g., config fields, headers) |
| **Cron entries** | Searches crontab for project-related entries |
| **Systemd units** | Lists matching systemd user services |

Each check returns `PASS`, `WARNING`, or `FAIL`. The overall status is the worst of all checks.

## Requirements

- Python 3.10+
- No external dependencies (stdlib only)

## Installation

```bash
# Just copy skill.py -- no pip install needed
cp skill.py /your/project/integrity_check.py
```

## Usage

### Quick scan (auto-detects common project files)

```bash
python3 skill.py
```

### With a configuration file

```bash
python3 skill.py --config checks.json
```

### Check a SQLite database

```bash
python3 skill.py --db data/app.db --config checks.json
```

### Write JSON report to file

```bash
python3 skill.py --output report.json
```

### Quiet mode (just print PASS/WARNING/FAIL)

```bash
python3 skill.py --quiet
```

### Check a different directory

```bash
python3 skill.py --dir /path/to/project
```

## Configuration

Create a JSON file with the checks you want:

```json
{
  "required_files": [
    "README.md",
    "pyproject.toml",
    "src/main.py"
  ],
  "required_dirs": [
    "src",
    "tests",
    "docs"
  ],
  "pipeline_files": [
    "scripts/deploy.sh",
    "scripts/backup.py"
  ],
  "stale_days": 30,
  "expected_tables": [
    "users",
    "sessions",
    "events"
  ],
  "required_content": {
    "pyproject.toml": ["[project]", "name ="],
    "README.md": ["## Installation", "## Usage"]
  },
  "cron_keyword": "myproject",
  "systemd_keyword": "myproject"
}
```

All fields are optional. Omit any you do not need.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed |
| 1 | At least one WARNING |
| 2 | At least one FAIL |

Use in CI/CD:

```bash
python3 skill.py --config checks.json --quiet || echo "Integrity issues detected"
```

## JSON report structure

```json
{
  "timestamp": "2025-01-15T14:30:00",
  "project_root": "/path/to/project",
  "overall_status": "WARNING",
  "summary": {"pass": 5, "warning": 1, "fail": 0},
  "checks": [
    {
      "name": "required_files",
      "status": "PASS",
      "details": { "files": [...], "missing": [] }
    }
  ]
}
```

## Integration with Claude Code

Add to your `CLAUDE.md`:

```markdown
## Integrity check
Run `python3 /path/to/skill.py --config checks.json` before commits to verify project health.
```
