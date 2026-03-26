#!/usr/bin/env python3
"""Integrity Guard — Codebase and data integrity checker.

A generic, extensible integrity check system that validates:
  1. File existence and consistency (expected files vs actual)
  2. SQLite database health (if a DB is present)
  3. Pipeline/script operational status
  4. Required document completeness
  5. Custom rule validation

Works standalone with zero external dependencies. Configure via a simple
JSON or Python dict to adapt to any project.

Usage:
    python3 skill.py                          # Run all checks on current directory
    python3 skill.py --config checks.json     # Run with custom config
    python3 skill.py --output report.json     # Write JSON report to file
    python3 skill.py --db path/to/db.sqlite   # Check a SQLite database
    python3 skill.py --dir /path/to/project   # Check a specific directory

Exit codes:
    0  All checks passed
    1  At least one WARNING
    2  At least one FAIL
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Default configuration -- override with --config or build programmatically
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict[str, Any] = {
    # Files that must exist (relative to project root)
    "required_files": [],

    # Directories that must exist
    "required_dirs": [],

    # Pipeline scripts to check (relative to project root)
    "pipeline_files": [],

    # Stale threshold in days (files older than this trigger a WARNING)
    "stale_days": 30,

    # SQLite tables that should exist (if --db is provided)
    "expected_tables": [],

    # Required fields/patterns in specific files (glob -> list of strings)
    "required_content": {},

    # Custom check: cron entries matching a keyword
    "cron_keyword": None,

    # Custom check: systemd units matching a keyword
    "systemd_keyword": None,
}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_required_files(root: Path, files: list[str]) -> dict[str, Any]:
    """Verify that all required files exist."""
    result: dict[str, Any] = {
        "name": "required_files",
        "status": "PASS",
        "details": {"files": [], "missing": []},
    }

    for fname in files:
        fpath = root / fname
        entry = {
            "name": fname,
            "exists": fpath.exists(),
            "size_bytes": fpath.stat().st_size if fpath.exists() else 0,
            "last_modified": (
                datetime.fromtimestamp(fpath.stat().st_mtime).isoformat()
                if fpath.exists() else None
            ),
        }
        result["details"]["files"].append(entry)
        if not fpath.exists():
            result["details"]["missing"].append(fname)

    if result["details"]["missing"]:
        result["status"] = "FAIL"

    return result


def check_required_dirs(root: Path, dirs: list[str]) -> dict[str, Any]:
    """Verify that all required directories exist."""
    result: dict[str, Any] = {
        "name": "required_directories",
        "status": "PASS",
        "details": {"dirs": [], "missing": []},
    }

    for dname in dirs:
        dpath = root / dname
        entry = {"name": dname, "exists": dpath.is_dir()}
        result["details"]["dirs"].append(entry)
        if not dpath.is_dir():
            result["details"]["missing"].append(dname)

    if result["details"]["missing"]:
        result["status"] = "FAIL"

    return result


def check_pipeline_status(
    root: Path, pipeline_files: list[str], stale_days: int = 30
) -> dict[str, Any]:
    """Check pipeline scripts: existence and freshness."""
    result: dict[str, Any] = {
        "name": "pipeline_status",
        "status": "PASS",
        "details": {"pipelines": [], "missing": [], "stale": []},
    }

    threshold = datetime.now() - timedelta(days=stale_days)

    for fname in pipeline_files:
        fpath = root / fname
        entry: dict[str, Any] = {
            "name": fname,
            "exists": fpath.exists(),
            "last_modified": None,
            "stale": False,
        }

        if fpath.exists():
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime)
            entry["last_modified"] = mtime.isoformat()
            if mtime < threshold:
                entry["stale"] = True
                result["details"]["stale"].append(fname)
        else:
            result["details"]["missing"].append(fname)

        result["details"]["pipelines"].append(entry)

    if result["details"]["missing"]:
        result["status"] = "FAIL"
    elif result["details"]["stale"]:
        result["status"] = "WARNING"

    return result


def check_database(db_path: Path, expected_tables: list[str]) -> dict[str, Any]:
    """Check SQLite database health: existence, table presence, row counts."""
    result: dict[str, Any] = {
        "name": "database_health",
        "status": "PASS",
        "details": {
            "db_path": str(db_path),
            "exists": db_path.exists(),
            "tables": [],
            "missing_tables": [],
        },
    }

    if not db_path.exists():
        result["status"] = "FAIL"
        result["details"]["error"] = "Database file not found"
        return result

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        actual_tables = {row[0] for row in cursor.fetchall()}

        for table in expected_tables:
            exists = table in actual_tables
            row_count = 0
            if exists:
                try:
                    row_count = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
                except sqlite3.OperationalError:
                    pass

            result["details"]["tables"].append({
                "name": table,
                "exists": exists,
                "row_count": row_count,
            })

            if not exists:
                result["details"]["missing_tables"].append(table)

        # Also report tables not in expected list
        extra = actual_tables - set(expected_tables)
        if extra:
            result["details"]["extra_tables"] = sorted(extra)

        conn.close()

        if result["details"]["missing_tables"]:
            result["status"] = "FAIL"

    except sqlite3.Error as e:
        result["status"] = "FAIL"
        result["details"]["error"] = str(e)

    return result


def check_required_content(root: Path, content_rules: dict[str, list[str]]) -> dict[str, Any]:
    """Check that specific files contain required strings/patterns."""
    result: dict[str, Any] = {
        "name": "required_content",
        "status": "PASS",
        "details": {"files": [], "incomplete": []},
    }

    for file_glob, required_strings in content_rules.items():
        matched_files = list(root.glob(file_glob))
        if not matched_files:
            result["details"]["incomplete"].append({
                "pattern": file_glob,
                "error": "no matching files",
            })
            result["status"] = "WARNING"
            continue

        for fpath in matched_files:
            try:
                content = fpath.read_text(encoding="utf-8")
            except Exception:
                content = ""

            missing = [s for s in required_strings if s not in content]
            entry = {
                "file": str(fpath.relative_to(root)),
                "missing_strings": missing,
            }
            result["details"]["files"].append(entry)
            if missing:
                result["details"]["incomplete"].append(entry)

    if result["details"]["incomplete"]:
        if result["status"] == "PASS":
            result["status"] = "WARNING"

    return result


def check_cron(keyword: str | None) -> dict[str, Any]:
    """Check crontab for entries matching a keyword."""
    result: dict[str, Any] = {
        "name": "cron_entries",
        "status": "PASS",
        "details": {"entries": [], "keyword": keyword},
    }

    if not keyword:
        result["details"]["skipped"] = True
        return result

    try:
        out = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0:
            for line in out.stdout.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and keyword.lower() in line.lower():
                    result["details"]["entries"].append(line)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        result["details"]["error"] = "crontab not available"

    return result


def check_systemd(keyword: str | None) -> dict[str, Any]:
    """Check systemd user units matching a keyword."""
    result: dict[str, Any] = {
        "name": "systemd_units",
        "status": "PASS",
        "details": {"units": [], "keyword": keyword},
    }

    if not keyword:
        result["details"]["skipped"] = True
        return result

    try:
        out = subprocess.run(
            ["systemctl", "list-units", "--user", "--type=service", "--no-pager", "-q"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            for line in out.stdout.strip().split("\n"):
                if keyword.lower() in line.lower():
                    result["details"]["units"].append(line.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        result["details"]["error"] = "systemctl not available"

    return result


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_all_checks(
    root: Path,
    config: dict[str, Any],
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Run all configured checks and produce a unified report."""
    checks: list[dict[str, Any]] = []

    if config.get("required_files"):
        checks.append(check_required_files(root, config["required_files"]))

    if config.get("required_dirs"):
        checks.append(check_required_dirs(root, config["required_dirs"]))

    if config.get("pipeline_files"):
        checks.append(
            check_pipeline_status(root, config["pipeline_files"], config.get("stale_days", 30))
        )

    if db_path:
        checks.append(check_database(db_path, config.get("expected_tables", [])))

    if config.get("required_content"):
        checks.append(check_required_content(root, config["required_content"]))

    checks.append(check_cron(config.get("cron_keyword")))
    checks.append(check_systemd(config.get("systemd_keyword")))

    # Summarize
    pass_count = sum(1 for c in checks if c["status"] == "PASS")
    warn_count = sum(1 for c in checks if c["status"] == "WARNING")
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")

    if fail_count > 0:
        overall = "FAIL"
    elif warn_count > 0:
        overall = "WARNING"
    else:
        overall = "PASS"

    return {
        "timestamp": datetime.now().isoformat(),
        "project_root": str(root),
        "overall_status": overall,
        "summary": {"pass": pass_count, "warning": warn_count, "fail": fail_count},
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Integrity Guard -- codebase integrity checker")
    parser.add_argument("--dir", "-d", default=".", help="Project root directory (default: cwd)")
    parser.add_argument("--config", "-c", help="JSON config file for check rules")
    parser.add_argument("--db", help="Path to SQLite database to check")
    parser.add_argument("--output", "-o", help="Write JSON report to this file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only print overall status")
    args = parser.parse_args()

    root = Path(args.dir).resolve()

    # Load config
    config = dict(DEFAULT_CONFIG)
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            config.update(user_config)
        else:
            print(f"Config file not found: {args.config}", file=sys.stderr)
            sys.exit(2)
    else:
        # Auto-detect: if no config given, do a basic filesystem scan
        # Check for common project files
        auto_required = []
        for candidate in ["README.md", "pyproject.toml", "package.json", "Makefile", "Cargo.toml"]:
            if (root / candidate).exists():
                auto_required.append(candidate)
        config["required_files"] = auto_required

    db_path = Path(args.db) if args.db else None

    report = run_all_checks(root, config, db_path)

    json_output = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(json_output, encoding="utf-8")
        print(f"Report written to {args.output}")

    if args.quiet:
        print(report["overall_status"])
    else:
        print(json_output)

    # Exit code
    if report["overall_status"] == "FAIL":
        sys.exit(2)
    elif report["overall_status"] == "WARNING":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
