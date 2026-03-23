#!/usr/bin/env python3
"""
T9 OS Smoke Tests — 핵심 파이프라인 최소 동작 확인
실행: python3 T9OS/tests/smoke_test.py
"""
import sys, os, subprocess, sqlite3, json
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent
WORKSPACE = T9.parent
DB_PATH = T9 / ".t9.db"

PASS, FAIL, SKIP = 0, 0, 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))

def skip(name, reason=""):
    global SKIP
    SKIP += 1
    print(f"  [SKIP] {name}" + (f" — {reason}" if reason else ""))

def run_cmd(cmd, timeout=30):
    """Run command and return (returncode, stdout, stderr)"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(T9))
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)

print("\n  === T9 OS Smoke Tests ===\n")

# 1. DB integrity
print("  --- DB ---")
try:
    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row
    check("DB 연결", True)

    count = conn.execute("SELECT COUNT(*) as c FROM entities").fetchone()["c"]
    check("엔티티 존재", count > 0, f"count={count}")

    # FTS5 test
    try:
        conn.execute("SELECT * FROM entities_fts LIMIT 1")
        check("FTS5 테이블 존재", True)
    except Exception as e:
        check("FTS5 테이블 존재", False, str(e))

    # Schema check
    cols = {r[1] for r in conn.execute("PRAGMA table_info(entities)").fetchall()}
    required = {"id", "filepath", "filename", "phase", "metadata", "body_preview", "file_hash", "updated_at"}
    missing = required - cols
    check("필수 컬럼 존재", not missing, f"missing={missing}" if missing else "")

    # No corrupted filepaths
    bad = conn.execute("SELECT COUNT(*) as c FROM entities WHERE typeof(filepath) != 'text' AND filepath IS NOT NULL").fetchone()["c"]
    check("filepath 타입 정합성", bad == 0, f"corrupted={bad}")

    conn.close()
except Exception as e:
    check("DB 연결", False, str(e))

# 2. t9_seed.py commands
print("\n  --- t9_seed.py ---")
rc, out, err = run_cmd(["python3", "t9_seed.py", "status"])
check("status 명령", rc == 0 and "T9 OS Seed" in out, err[:100] if rc else "")

rc, out, err = run_cmd(["python3", "t9_seed.py", "search", "test"])
check("search 명령", rc == 0, err[:100] if rc else "")

rc, out, err = run_cmd(["python3", "t9_seed.py", "orphans"])
check("orphans 명령", rc == 0, err[:100] if rc else "")

# 3. Key files exist
print("\n  --- 핵심 파일 ---")
key_files = [
    "t9_seed.py", "lib/config.py", "lib/logger.py", "lib/commands.py",
    "lib/parsers.py", "lib/ipc.py", "lib/transduction.py",
    "pipes/t9_bot.py", "pipes/healthcheck.py", "pipes/cron_runner.sh",
    "pipes/gm_batch.py", "pipes/calendar_sync.py", "pipes/deadline_notify.py",
    "pipes/t9_ceo_brief.py",
    "constitution/L1_execution.md", "constitution/L2_interpretation.md",
    "constitution/L3_amendment.md", "constitution/GUARDIANS.md",
]
for f in key_files:
    p = T9 / f
    check(f"파일: {f}", p.exists())

# 4. Config imports
print("\n  --- 모듈 임포트 ---")
rc, out, err = run_cmd(["python3", "-c", "from lib.config import *; print('OK')"])
check("lib.config 임포트", rc == 0 and "OK" in out, err[:100] if rc else "")

rc, out, err = run_cmd(["python3", "-c", "from lib.logger import *; print('OK')"])
check("lib.logger 임포트", rc == 0 and "OK" in out, err[:100] if rc else "")

rc, out, err = run_cmd(["python3", "-c", "from lib.parsers import *; print('OK')"])
check("lib.parsers 임포트", rc == 0 and "OK" in out, err[:100] if rc else "")

# Summary
print(f"\n  === 결과: PASS={PASS} FAIL={FAIL} SKIP={SKIP} ===")
print(f"  {'ALL CLEAR' if FAIL == 0 else f'FAILURES: {FAIL}'}\n")
sys.exit(0 if FAIL == 0 else 1)
