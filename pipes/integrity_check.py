#!/usr/bin/env python3
"""T9 OS Data Integrity Check System.

Validates:
  1. Entity consistency (DB vs files)
  2. Pipeline operational status
  3. Constitution completeness
  4. Transition history validity
  5. Preindividual (inbox) coverage
  6. ADR completeness

Usage:
  python3 T9OS/pipes/integrity_check.py
  python3 T9OS/pipes/integrity_check.py --output /path/to/output.json
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ──────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent  # T9OS/
DB_PATH = BASE / ".t9.db"
INBOX_DIR = BASE / "field" / "inbox"
CONSTITUTION_DIR = BASE / "constitution"
DECISIONS_DIR = BASE / "decisions"
PIPES_DIR = BASE / "pipes"

HANBEEN_ROOT = BASE.parent  # ~/code/HANBEEN/
CC_LOGS_DIR = HANBEEN_ROOT / "_ai" / "logs" / "cc"
CX_LOGS_DIR = HANBEEN_ROOT / "_ai" / "logs" / "cx"
T9D_PUBLIC = HANBEEN_ROOT / "PROJECTS" / "t9-dashboard" / "public"

# Valid Simondon phase transitions (from -> set of valid to)
VALID_PHASES = [
    "preindividual",
    "impulse",
    "tension_detected",
    "candidate_generated",
    "individuating",
    "stabilized",
    "split",
    "merged",
    "reactivated",
    "suspended",
    "sediment",
    "archived",
    "dissolved",
]

# Permissive validation: any forward/sideways transition is valid.
# Strict enforcement is done at runtime by t9_seed.py TRANSITIONS.
# This check catches only clearly invalid backward transitions.
VALID_TRANSITIONS = {
    "preindividual": {"impulse", "tension_detected", "candidate_generated", "individuating", "stabilized", "archived", "dissolved", "sediment"},
    "impulse": {"tension_detected", "candidate_generated", "individuating", "stabilized", "archived", "dissolved", "preindividual", "sediment"},
    "tension_detected": {"candidate_generated", "individuating", "stabilized", "archived", "dissolved", "suspended", "sediment", "preindividual"},
    "candidate_generated": {"individuating", "stabilized", "archived", "dissolved", "suspended", "sediment"},
    "individuating": {"tension_detected", "stabilized", "split", "merged", "archived", "dissolved", "suspended", "sediment", "preindividual"},
    "stabilized": {"archived", "dissolved", "split", "merged", "suspended", "reactivated", "sediment", "individuating", "tension_detected", "preindividual"},
    "split": {"preindividual", "tension_detected", "candidate_generated", "individuating", "suspended"},
    "merged": {"preindividual", "tension_detected", "candidate_generated", "individuating", "suspended"},
    "reactivated": {"tension_detected", "candidate_generated", "individuating", "stabilized"},
    "suspended": {"reactivated", "archived", "sediment", "dissolved"},
    "sediment": {"reactivated", "archived", "dissolved", "preindividual", "individuating"},
    "archived": {"reactivated", "dissolved", "preindividual", "individuating"},
    "dissolved": {"sediment", "preindividual"},
}

# Pipeline registry from CLAUDE.md
PIPELINE_REGISTRY = {
    "gm_batch.py": "Guardian batch + review",
    "t9_auto.py": "Preindividual auto-classification",
    "t9_ceo_brief.py": "CEO Telegram brief",
    "t9_bot.py": "Telegram bot",
    "deadline_notify.py": "Deadline notification",
    "session_lock.py": "Session collision prevention",
    "tg_common.py": "Telegram common functions",
    "calendar_sync.py": "Google Calendar sync",
    "intent_parser.py": "Intent parser (5-axis)",
    "whisper_pipeline.py": "Whisper transcription",
    "sc41_cron.py": "SC41 automation",
    "reproducibility_check.py": "Reproducibility check",
}

ADR_REQUIRED_FIELDS = ["날짜", "상태", "결정", "이유"]


def get_db_connection():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ── Check 1: Entity Consistency ────────────────────────
def check_entity_consistency():
    result = {
        "name": "entity_consistency",
        "status": "PASS",
        "details": {
            "db_count": 0,
            "file_count": 0,
            "orphans": [],
            "unindexed": [],
            "duplicates": [],
            "inbox_db_count": 0,
            "inbox_file_count": 0,
        },
    }

    conn = get_db_connection()
    if not conn:
        result["status"] = "FAIL"
        result["details"]["error"] = "Database not found"
        return result

    try:
        # Total DB entities
        total_cursor = conn.execute("SELECT COUNT(*) FROM entities")
        result["details"]["db_count"] = total_cursor.fetchone()[0]

        # All entities - check file existence against T9OS root
        cursor = conn.execute("SELECT id, filepath, filename FROM entities")
        db_entities = cursor.fetchall()

        orphans = []
        filepath_counts = {}
        for row in db_entities:
            fp = row["filepath"]
            if not fp:
                continue

            # Track duplicates by filepath
            if fp in filepath_counts:
                filepath_counts[fp].append(row["id"])
            else:
                filepath_counts[fp] = [row["id"]]

            # Check file existence (filepath is relative to T9OS)
            full_path = BASE / fp
            if not full_path.exists():
                orphans.append({
                    "filename": row["filename"] or os.path.basename(fp),
                    "filepath": fp,
                    "ids": [row["id"]],
                })

        # Limit orphan output to 30 for readability
        result["details"]["orphans"] = orphans[:30]
        result["details"]["orphan_count"] = len(orphans)

        # Inbox-specific: files in inbox dir vs DB (only scan indexable extensions)
        SCAN_EXTS = {".md", ".docx", ".xlsx", ".pdf", ".hwp", ".txt", ".csv", ".log",
                     ".zip", ".jpg", ".jpeg", ".png", ".mp4", ".svg"}
        inbox_files = set()
        if INBOX_DIR.exists():
            inbox_files = {f.name for f in INBOX_DIR.iterdir() if f.is_file() and f.suffix in SCAN_EXTS}
        result["details"]["inbox_file_count"] = len(inbox_files)

        inbox_cursor = conn.execute(
            "SELECT id, filepath, filename FROM entities WHERE filepath LIKE 'field/inbox/%'"
        )
        inbox_entities = inbox_cursor.fetchall()
        result["details"]["inbox_db_count"] = len(inbox_entities)
        inbox_db_filenames = {
            (row["filename"] or os.path.basename(row["filepath"] or ""))
            for row in inbox_entities
        }

        # Unindexed inbox files
        unindexed = [f for f in inbox_files if f not in inbox_db_filenames]
        result["details"]["unindexed"] = unindexed[:30]
        result["details"]["unindexed_count"] = len(unindexed)

        # Duplicates: same filepath, multiple records
        duplicates = []
        for fp, ids in filepath_counts.items():
            if len(ids) > 1:
                duplicates.append({"filepath": fp, "ids": ids})
        result["details"]["duplicates"] = duplicates

        # Count actual files tracked
        result["details"]["file_count"] = result["details"]["inbox_file_count"]

        # Determine status
        if duplicates:
            result["status"] = "WARNING"
        if len(unindexed) > 5:
            result["status"] = "WARNING"
        if len(orphans) > 50:
            result["status"] = "FAIL"
        elif len(orphans) > 10:
            if result["status"] == "PASS":
                result["status"] = "WARNING"

    finally:
        conn.close()

    return result


# ── Check 2: Pipeline Status ──────────────────────────
def check_pipeline_status():
    result = {
        "name": "pipeline_status",
        "status": "PASS",
        "details": {
            "pipelines": [],
            "missing_files": [],
            "stale_pipelines": [],
            "systemd_units": [],
            "cron_entries": [],
        },
    }

    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)

    for filename, description in PIPELINE_REGISTRY.items():
        filepath = PIPES_DIR / filename
        entry = {
            "name": filename,
            "description": description,
            "exists": filepath.exists(),
            "last_modified": None,
            "stale": False,
        }

        if filepath.exists():
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            entry["last_modified"] = mtime.isoformat()
            if mtime < thirty_days_ago:
                entry["stale"] = True
                result["details"]["stale_pipelines"].append(filename)
        else:
            result["details"]["missing_files"].append(filename)

        result["details"]["pipelines"].append(entry)

    # Check systemd units
    try:
        out = subprocess.run(
            ["systemctl", "list-units", "--user", "--type=service", "--no-pager", "-q"],
            capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0:
            for line in out.stdout.strip().split("\n"):
                if "t9" in line.lower():
                    result["details"]["systemd_units"].append(line.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check crontab
    try:
        out = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0:
            for line in out.stdout.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and "t9" in line.lower():
                    result["details"]["cron_entries"].append(line)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Determine status
    if result["details"]["missing_files"]:
        result["status"] = "FAIL"
    elif result["details"]["stale_pipelines"]:
        result["status"] = "WARNING"

    return result


# ── Check 3: Constitution Completeness ─────────────────
def check_constitution():
    result = {
        "name": "constitution_completeness",
        "status": "PASS",
        "details": {
            "files": [],
            "missing": [],
        },
    }

    required = ["L1_execution.md", "L2_interpretation.md", "L3_amendment.md", "GUARDIANS.md"]

    for fname in required:
        fpath = CONSTITUTION_DIR / fname
        entry = {
            "name": fname,
            "exists": fpath.exists(),
            "last_modified": None,
            "size_bytes": 0,
        }

        if fpath.exists():
            stat = fpath.stat()
            entry["last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            entry["size_bytes"] = stat.st_size
        else:
            result["details"]["missing"].append(fname)

        result["details"]["files"].append(entry)

    if result["details"]["missing"]:
        result["status"] = "FAIL"

    return result


# ── Check 4: Transition History Validity ───────────────
def check_transitions():
    result = {
        "name": "transition_history",
        "status": "PASS",
        "details": {
            "total_transitions": 0,
            "checked": 0,
            "invalid_transitions": [],
            "timestamp_reversals": [],
        },
    }

    conn = get_db_connection()
    if not conn:
        result["status"] = "FAIL"
        result["details"]["error"] = "Database not found"
        return result

    try:
        cursor = conn.execute(
            "SELECT id, entity_id, from_phase, to_phase, timestamp, reason "
            "FROM transitions ORDER BY timestamp DESC LIMIT 100"
        )
        rows = cursor.fetchall()
        result["details"]["total_transitions"] = len(rows)
        result["details"]["checked"] = len(rows)

        prev_ts = None
        for row in rows:
            from_p = row["from_phase"]
            to_p = row["to_phase"]
            ts = row["timestamp"]

            # Check valid transition
            if from_p and to_p:
                valid_targets = VALID_TRANSITIONS.get(from_p, set())
                if to_p not in valid_targets and from_p != to_p:
                    result["details"]["invalid_transitions"].append({
                        "id": row["id"],
                        "entity_id": row["entity_id"],
                        "from": from_p,
                        "to": to_p,
                        "timestamp": ts,
                    })

            # Check timestamp ordering (we're iterating DESC, so prev_ts should be >= ts)
            if prev_ts and ts:
                # Within same entity, check for reversals
                pass  # Timestamps are already DESC ordered by query
            prev_ts = ts

        # Check per-entity timestamp ordering
        entity_cursor = conn.execute(
            "SELECT entity_id, timestamp FROM transitions ORDER BY entity_id, timestamp"
        )
        entity_rows = entity_cursor.fetchall()
        current_entity = None
        last_ts = None
        for row in entity_rows:
            if row["entity_id"] != current_entity:
                current_entity = row["entity_id"]
                last_ts = row["timestamp"]
                continue
            if last_ts and row["timestamp"] and row["timestamp"] < last_ts:
                result["details"]["timestamp_reversals"].append({
                    "entity_id": row["entity_id"],
                    "earlier_ts": row["timestamp"],
                    "later_ts": last_ts,
                })
            last_ts = row["timestamp"]

        if result["details"]["invalid_transitions"]:
            result["status"] = "WARNING"
        if result["details"]["timestamp_reversals"]:
            result["status"] = "FAIL"

    finally:
        conn.close()

    return result


# ── Check 5: Preindividual Coverage ────────────────────
def check_preindividual_coverage():
    result = {
        "name": "preindividual_coverage",
        "status": "PASS",
        "details": {
            "total_inbox_files": 0,
            "unregistered": [],
            "recent_24h_total": 0,
            "recent_24h_unregistered": 0,
            "recent_24h_ratio": 0.0,
        },
    }

    conn = get_db_connection()
    if not conn:
        result["status"] = "FAIL"
        result["details"]["error"] = "Database not found"
        return result

    try:
        # Get all inbox files
        inbox_files = []
        if INBOX_DIR.exists():
            inbox_files = [f for f in INBOX_DIR.iterdir() if f.is_file() and f.suffix == ".md"]
        result["details"]["total_inbox_files"] = len(inbox_files)

        # Get all registered filepaths
        cursor = conn.execute("SELECT filepath FROM entities")
        registered = {row["filepath"] for row in cursor.fetchall()}

        now = datetime.now()
        twenty_four_hours_ago = now - timedelta(hours=24)

        for f in inbox_files:
            relative = f"field/inbox/{f.name}"
            if relative not in registered:
                result["details"]["unregistered"].append(f.name)

            # Check if created in last 24h
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime >= twenty_four_hours_ago:
                    result["details"]["recent_24h_total"] += 1
                    if relative not in registered:
                        result["details"]["recent_24h_unregistered"] += 1
            except OSError:
                pass

        if result["details"]["recent_24h_total"] > 0:
            result["details"]["recent_24h_ratio"] = round(
                result["details"]["recent_24h_unregistered"] / result["details"]["recent_24h_total"],
                2,
            )

        if len(result["details"]["unregistered"]) > 5:
            result["status"] = "WARNING"
        if result["details"]["recent_24h_ratio"] > 0.5:
            result["status"] = "FAIL"

    finally:
        conn.close()

    return result


# ── Check 6: ADR Completeness ──────────────────────────
def check_adr_completeness():
    result = {
        "name": "adr_completeness",
        "status": "PASS",
        "details": {
            "total_adrs": 0,
            "adrs": [],
            "incomplete_adrs": [],
            "cc_log_count": 0,
            "cx_log_count": 0,
        },
    }

    # Count logs
    if CC_LOGS_DIR.exists():
        result["details"]["cc_log_count"] = len([
            f for f in CC_LOGS_DIR.iterdir() if f.is_file()
        ])
    if CX_LOGS_DIR.exists():
        result["details"]["cx_log_count"] = len([
            f for f in CX_LOGS_DIR.iterdir() if f.is_file()
        ])

    # Check ADR files
    if not DECISIONS_DIR.exists():
        result["status"] = "FAIL"
        result["details"]["error"] = "Decisions directory not found"
        return result

    adr_files = sorted([f for f in DECISIONS_DIR.iterdir() if (f.name.startswith("ADR-") or f.name[:3].isdigit()) and f.suffix == ".md"])
    result["details"]["total_adrs"] = len(adr_files)

    for adr_file in adr_files:
        try:
            content = adr_file.read_text(encoding="utf-8")
        except Exception:
            content = ""

        entry = {
            "filename": adr_file.name,
            "has_required_fields": True,
            "missing_fields": [],
        }

        for field in ADR_REQUIRED_FIELDS:
            # Check for field presence (as "- 필드:" or "필드:" pattern)
            if field + ":" not in content and f"- {field}:" not in content:
                entry["has_required_fields"] = False
                entry["missing_fields"].append(field)

        result["details"]["adrs"].append(entry)
        if not entry["has_required_fields"]:
            result["details"]["incomplete_adrs"].append(entry["filename"])

    if result["details"]["incomplete_adrs"]:
        result["status"] = "WARNING"

    return result


# ── Main ───────────────────────────────────────────────
def run_all_checks():
    checks = [
        check_entity_consistency(),
        check_pipeline_status(),
        check_constitution(),
        check_transitions(),
        check_preindividual_coverage(),
        check_adr_completeness(),
    ]

    pass_count = sum(1 for c in checks if c["status"] == "PASS")
    warn_count = sum(1 for c in checks if c["status"] == "WARNING")
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")

    if fail_count > 0:
        overall = "FAIL"
    elif warn_count > 0:
        overall = "WARNING"
    else:
        overall = "PASS"

    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": overall,
        "checks": checks,
        "summary": {
            "pass": pass_count,
            "warning": warn_count,
            "fail": fail_count,
        },
    }

    return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="T9 OS Data Integrity Check")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    args = parser.parse_args()

    report = run_all_checks()

    json_output = json.dumps(report, ensure_ascii=False, indent=2)

    # Write to T9D public directory
    t9d_output = T9D_PUBLIC / "integrity.json"
    try:
        t9d_output.parent.mkdir(parents=True, exist_ok=True)
        t9d_output.write_text(json_output, encoding="utf-8")
    except Exception as e:
        print(f"Warning: Could not write to {t9d_output}: {e}", file=sys.stderr)

    # Write to custom output if specified
    if args.output:
        try:
            Path(args.output).write_text(json_output, encoding="utf-8")
        except Exception as e:
            print(f"Warning: Could not write to {args.output}: {e}", file=sys.stderr)

    # Always print to stdout
    print(json_output)


if __name__ == "__main__":
    main()
