#!/usr/bin/env python3
"""T9 OS — pipeline state.

session-start.shauto call. .

Usage:
    python3 T9OS/pipes/healthcheck.py          # output
    python3 T9OS/pipes/healthcheck.py --json    # JSON output
    python3 T9OS/pipes/healthcheck.py --tg      # Telegram notification
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import (
    T9, HANBEEN, DB_PATH, GEMINI_KEY, TG_TOKEN, TG_CHAT,
    CANVAS_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_REFRESH_TOKEN,
)
from lib.logger import get_all_status, _tg_send_raw
from lib.registry import PIPELINE_REGISTRY, DAEMON_PROCESSES, CRON_IDENTIFIERS

# ─── item definition (lib/registry.py single source) ────────────────────────────────────────
# SRBB: duplicate definitionregistry.py
PIPELINES = [{"name": p["file"], "path": p["path"], "type": p["type"]} for p in PIPELINE_REGISTRY]

REQUIRED_KEYS = [
    ("TG_TOKEN", TG_TOKEN, "Telegram bot"),
    ("TG_CHAT", TG_CHAT, "Telegram "),
    ("GEMINI_KEY", GEMINI_KEY, "Gemini API (t9_auto, gm_batch)"),
    ("CANVAS_TOKEN", CANVAS_TOKEN, "Canvas LMS (sc41)"),
    ("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID, "Google Calendar"),
    ("GOOGLE_REFRESH_TOKEN", GOOGLE_REFRESH_TOKEN, "Google Calendar"),
]


def check_files() -> list[dict]:
    """pipeline file check."""
    results = []
    for p in PIPELINES:
        exists = p["path"].exists()
        results.append({
            "name": p["name"],
            "type": p["type"],
            "exists": exists,
            "status": "OK" if exists else "MISSING",
        })
    return results


def check_env() -> list[dict]:
    """required env var/API key check."""
    results = []
    for name, value, desc in REQUIRED_KEYS:
        ok = bool(value and len(value) > 3)
        results.append({
            "name": name,
            "desc": desc,
            "status": "OK" if ok else "MISSING",
        })
    return results


def check_processes() -> list[dict]:
    """execution pipeline process check (duplicate )."""
    results = []
    try:
        ps = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        )
        lines = ps.stdout.splitlines()
    except Exception:
        return [{"name": "ps", "status": "ERROR", "detail": "ps execution failed"}]

    daemon_names = ["t9_bot.py", "deadline_notify", "calendar_sync"]
    for name in daemon_names:
        matches = [l for l in lines if name in l and "grep" not in l and "python" in l]
        if len(matches) == 0:
            if name == "t9_bot.py":
                results.append({"name": name, "status": "DOWN", "pids": [], "detail": "process not found"})
        elif len(matches) == 1:
            pid = matches[0].split()[1]
            results.append({"name": name, "status": "OK", "pids": [pid], "detail": ""})
        else:
            pids = [m.split()[1] for m in matches]
            results.append({"name": name, "status": "DUPLICATE", "pids": pids, "detail": f"duplicate {len(matches)}"})

    return results


def check_cron() -> list[dict]:
    """crontab register check."""
    results = []
    try:
        cron = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, timeout=5
        )
        cron_content = cron.stdout
    except Exception:
        return [{"name": "crontab", "status": "ERROR", "detail": "crontab  failed"}]

    expected_cron = [
        ("deadline_notify", "deadline"),
        ("ceo_brief", "ceo_brief"),
        ("t9_auto", "t9_auto"),
        ("calendar_sync", "calendar"),
        ("sc41_cron", "sc41"),
        ("tidy", "tidy"),
    ]
    for name, pattern in expected_cron:
        found = pattern in cron_content
        results.append({
            "name": name,
            "status": "OK" if found else "NOT_REGISTERED",
        })

    return results


def check_pipe_status() -> list[dict]:
    """lib/loggerpipeline execution record check."""
    status = get_all_status()
    results = []
    for name, info in status.items():
        if name == "test_pipe":
            continue
        results.append({
            "name": name,
            "status": info.get("status", "UNKNOWN"),
            "time": info.get("time", ""),
            "detail": info.get("detail", "")[:100],
        })
    return results


def check_db() -> dict:
    """SQLite DB state."""
    if not DB_PATH.exists():
        return {"status": "MISSING", "detail": ".t9.db not found"}
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        conn.close()
        return {"status": "OK", "entities": count}
    except Exception as e:
        # path/query : logdetail, TGmessage
        import logging
        logging.getLogger("healthcheck").warning("DB check failed: %s", e)
        return {"status": "ERROR", "detail": "DB access failed ( log check)"}


def run_all() -> dict:
    """total execution."""
    return {
        "timestamp": datetime.now().isoformat(),
        "files": check_files(),
        "env": check_env(),
        "processes": check_processes(),
        "cron": check_cron(),
        "pipe_status": check_pipe_status(),
        "db": check_db(),
    }


def format_terminal(result: dict) -> str:
    """."""
    lines = [f"\n  === T9 OS Health Check ({result['timestamp'][:19]}) ===\n"]

    # env var
    env_issues = [e for e in result["env"] if e["status"] != "OK"]
    if env_issues:
        lines.append("  ❌ env var missing:")
        for e in env_issues:
            lines.append(f"     {e['name']} — {e['desc']}")
    else:
        lines.append(f"  ✅ env var {len(result['env'])} normal")

    # file
    missing = [f for f in result["files"] if f["status"] != "OK"]
    if missing:
        lines.append(f"  ❌ file missing: {', '.join(f['name'] for f in missing)}")
    else:
        lines.append(f"  ✅ pipeline {len(result['files'])} file ")

    # process
    for p in result["processes"]:
        if p["status"] == "DUPLICATE":
            lines.append(f"  ⚠️ {p['name']} duplicate! PIDs={p['pids']}")
        elif p["status"] == "DOWN":
            lines.append(f"  ❌ {p['name']} process not found")
        elif p["status"] == "OK":
            lines.append(f"  ✅ {p['name']} PID={p['pids'][0]}")

    # cron
    cron_issues = [c for c in result["cron"] if c["status"] != "OK"]
    if cron_issues:
        lines.append(f"  ⚠️ cron register: {', '.join(c['name'] for c in cron_issues)}")
    else:
        lines.append(f"  ✅ cron {len(result['cron'])} register")

    # pipeline execution state
    fails = [p for p in result["pipe_status"] if p["status"] == "FAIL"]
    if fails:
        lines.append("  ❌  failed:")
        for f in fails:
            lines.append(f"     {f['name']} ({f['time']}) — {f['detail'][:60]}")

    # DB
    db = result["db"]
    if db["status"] == "OK":
        lines.append(f"  ✅ DB normal ( {db.get('entities', '?')}items)")
    else:
        lines.append(f"  ❌ DB {db['status']}: {db.get('detail', '')}")

    #
    total_issues = len(env_issues) + len(missing) + len(cron_issues) + len(fails)
    total_issues += sum(1 for p in result["processes"] if p["status"] in ("DUPLICATE", "DOWN"))
    if db["status"] != "OK":
        total_issues += 1

    if total_issues == 0:
        lines.append("\n  🟢 total normal")
    else:
        lines.append(f"\n  🔴  {total_issues}items found")

    return "\n".join(lines)


if __name__ == "__main__":
    result = run_all()

    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif "--tg" in sys.argv:
        text = format_terminal(result)
        # TG path/detail remove — state
        issues = [l for l in text.split("\n") if "❌" in l or "⚠️" in l]
        if issues:
            # detail partial : content remove
            import re
            sanitized = [re.sub(r'\(.*?\)', '', l).strip() for l in issues]
            try:
                _tg_send_raw("🔴 T9 Health Check\n\n" + "\n".join(sanitized))
            except Exception:
                print("  [warn] TG notification failed")
            print(text)  # total
        else:
            print("  🟢 total normal — TG notification skipped")
    else:
        print(format_terminal(result))
