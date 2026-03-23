#!/usr/bin/env python3
"""T9 OS 헬스체크 — 모든 파이프라인 상태를 한눈에.

session-start.sh에서 자동 호출. 문제 있으면 즉시 표시.

사용법:
    python3 T9OS/pipes/healthcheck.py          # 터미널 출력
    python3 T9OS/pipes/healthcheck.py --json    # JSON 출력
    python3 T9OS/pipes/healthcheck.py --tg      # 문제 있으면 텔레그램 알림
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import (
    T9, WORKSPACE, DB_PATH, GEMINI_KEY, TG_TOKEN, TG_CHAT,
    CANVAS_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_REFRESH_TOKEN,
)
from lib.logger import get_all_status, _tg_send_raw

# ─── 체크 항목 정의 ──────────────────────────────────────────

PIPELINES = [
    {"name": "t9_seed.py", "path": T9 / "t9_seed.py", "type": "engine"},
    {"name": "t9_bot.py", "path": T9 / "pipes" / "t9_bot.py", "type": "daemon"},
    {"name": "t9_auto.py", "path": T9 / "pipes" / "t9_auto.py", "type": "cron"},
    {"name": "gm_batch.py", "path": T9 / "pipes" / "gm_batch.py", "type": "manual"},
    {"name": "deadline_notify.py", "path": T9 / "pipes" / "deadline_notify.py", "type": "cron"},
    {"name": "ceo_brief.py", "path": T9 / "pipes" / "t9_ceo_brief.py", "type": "cron"},
    {"name": "calendar_sync.py", "path": T9 / "pipes" / "calendar_sync.py", "type": "cron"},
    {"name": "coursework_cron.py", "path": T9 / "pipes" / "coursework_cron.py", "type": "cron"},
    {"name": "integrity_check.py", "path": T9 / "pipes" / "integrity_check.py", "type": "check"},
    {"name": "session_lock.py", "path": T9 / "pipes" / "session_lock.py", "type": "lib"},
    {"name": "tg_common.py", "path": T9 / "pipes" / "tg_common.py", "type": "lib"},
    {"name": "adr_auto.py", "path": T9 / "pipes" / "adr_auto.py", "type": "hook"},
    {"name": "whisper_pipeline.py", "path": T9 / "pipes" / "whisper_pipeline.py", "type": "manual"},
]

REQUIRED_KEYS = [
    ("TG_TOKEN", TG_TOKEN, "텔레그램 봇"),
    ("TG_CHAT", TG_CHAT, "텔레그램 챗"),
    ("GEMINI_KEY", GEMINI_KEY, "Gemini API (t9_auto, gm_batch)"),
    ("CANVAS_TOKEN", CANVAS_TOKEN, "Canvas LMS (coursework)"),
    ("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID, "Google Calendar"),
    ("GOOGLE_REFRESH_TOKEN", GOOGLE_REFRESH_TOKEN, "Google Calendar"),
]


def check_files() -> list[dict]:
    """파이프라인 파일 존재 확인."""
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
    """필수 환경변수/API 키 확인."""
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
    """실행 중인 파이프라인 프로세스 확인 (중복 감지)."""
    results = []
    try:
        ps = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        )
        lines = ps.stdout.splitlines()
    except Exception:
        return [{"name": "ps", "status": "ERROR", "detail": "ps 실행 실패"}]

    daemon_names = ["t9_bot.py", "deadline_notify", "calendar_sync"]
    for name in daemon_names:
        matches = [l for l in lines if name in l and "grep" not in l and "python" in l]
        if len(matches) == 0:
            if name == "t9_bot.py":
                results.append({"name": name, "status": "DOWN", "pids": [], "detail": "프로세스 없음"})
        elif len(matches) == 1:
            pid = matches[0].split()[1]
            results.append({"name": name, "status": "OK", "pids": [pid], "detail": ""})
        else:
            pids = [m.split()[1] for m in matches]
            results.append({"name": name, "status": "DUPLICATE", "pids": pids, "detail": f"중복 {len(matches)}개"})

    return results


def check_cron() -> list[dict]:
    """crontab 등록 확인."""
    results = []
    try:
        cron = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, timeout=5
        )
        cron_content = cron.stdout
    except Exception:
        return [{"name": "crontab", "status": "ERROR", "detail": "crontab 읽기 실패"}]

    expected_cron = [
        ("deadline_notify", "deadline"),
        ("ceo_brief", "ceo_brief"),
        ("t9_auto", "t9_auto"),
        ("calendar_sync", "calendar"),
        ("coursework_cron", "coursework"),
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
    """lib/logger의 파이프라인 실행 기록 확인."""
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
    """SQLite DB 상태."""
    if not DB_PATH.exists():
        return {"status": "MISSING", "detail": ".t9.db 없음"}
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        conn.close()
        return {"status": "OK", "entities": count}
    except Exception as e:
        return {"status": "ERROR", "detail": str(e)[:100]}


def run_all() -> dict:
    """전체 헬스체크 실행."""
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
    """터미널용 포맷."""
    lines = [f"\n  === T9 OS Health Check ({result['timestamp'][:19]}) ===\n"]

    # 환경변수
    env_issues = [e for e in result["env"] if e["status"] != "OK"]
    if env_issues:
        lines.append("  ❌ 환경변수 누락:")
        for e in env_issues:
            lines.append(f"     {e['name']} — {e['desc']}")
    else:
        lines.append(f"  ✅ 환경변수 {len(result['env'])}개 정상")

    # 파일
    missing = [f for f in result["files"] if f["status"] != "OK"]
    if missing:
        lines.append(f"  ❌ 파일 누락: {', '.join(f['name'] for f in missing)}")
    else:
        lines.append(f"  ✅ 파이프라인 {len(result['files'])}개 파일 존재")

    # 프로세스
    for p in result["processes"]:
        if p["status"] == "DUPLICATE":
            lines.append(f"  ⚠️ {p['name']} 중복! PIDs={p['pids']}")
        elif p["status"] == "DOWN":
            lines.append(f"  ❌ {p['name']} 프로세스 없음")
        elif p["status"] == "OK":
            lines.append(f"  ✅ {p['name']} PID={p['pids'][0]}")

    # cron
    cron_issues = [c for c in result["cron"] if c["status"] != "OK"]
    if cron_issues:
        lines.append(f"  ⚠️ cron 미등록: {', '.join(c['name'] for c in cron_issues)}")
    else:
        lines.append(f"  ✅ cron {len(result['cron'])}개 등록")

    # 최근 파이프라인 실행 상태
    fails = [p for p in result["pipe_status"] if p["status"] == "FAIL"]
    if fails:
        lines.append("  ❌ 최근 실패:")
        for f in fails:
            lines.append(f"     {f['name']} ({f['time']}) — {f['detail'][:60]}")

    # DB
    db = result["db"]
    if db["status"] == "OK":
        lines.append(f"  ✅ DB 정상 (엔티티 {db.get('entities', '?')}건)")
    else:
        lines.append(f"  ❌ DB {db['status']}: {db.get('detail', '')}")

    # 종합
    total_issues = len(env_issues) + len(missing) + len(cron_issues) + len(fails)
    total_issues += sum(1 for p in result["processes"] if p["status"] in ("DUPLICATE", "DOWN"))
    if db["status"] != "OK":
        total_issues += 1

    if total_issues == 0:
        lines.append("\n  🟢 전체 정상")
    else:
        lines.append(f"\n  🔴 문제 {total_issues}건 발견")

    return "\n".join(lines)


if __name__ == "__main__":
    result = run_all()

    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif "--tg" in sys.argv:
        text = format_terminal(result)
        issues = [l for l in text.split("\n") if "❌" in l or "⚠️" in l]
        if issues:
            _tg_send_raw("🔴 T9 Health Check\n\n" + "\n".join(issues))
            print(text)
        else:
            print("  🟢 전체 정상 — TG 알림 생략")
    else:
        print(format_terminal(result))
