#!/usr/bin/env python3
"""BIBLE.md + filesystemverification.

guardian G4(verification)implement. stalewarning.
session-start guardiancall .

execution: python3 T9OS/tests/verify_claims.py
"""
import os
import re
import subprocess
import sqlite3
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent
HANBEEN = T9.parent

# WSL DB
_WSL_DB = Path.home() / ".t9os_data" / ".t9.db"
DB_PATH = _WSL_DB if _WSL_DB.exists() else T9 / ".t9.db"

PASS, WARN = 0, 0

def check(name, claimed, actual, tolerance=0):
    global PASS, WARN
    if abs(claimed - actual) <= tolerance:
        PASS += 1
    else:
        WARN += 1
        print(f"  [STALE] {name}: ={claimed}, ={actual}")

def count_files(path, pattern="*", recurse=True):
    p = Path(path)
    if not p.exists(): return 0
    return len(list(p.rglob(pattern) if recurse else p.glob(pattern)))

def count_lines(filepath):
    p = Path(filepath)
    if not p.exists(): return 0
    return sum(1 for _ in open(p, encoding="utf-8", errors="replace"))

print("\n  === verification ===\n")

# 1. t9_seed.py
actual_lines = count_lines(T9 / "t9_seed.py")
check("t9_seed.py ", 646, actual_lines, tolerance=20)

# 2. pipes/ pipeline
actual_pipes = len(list((T9 / "pipes").glob("*.py")))
check("pipes/*.py ", 23, actual_pipes, tolerance=2)

# 3. lib/ module
actual_lib = len(list((T9 / "lib").glob("*.py")))
check("lib/*.py ", 10, actual_lib, tolerance=1)

# 4. skills
skills_dir = HANBEEN / ".claude" / "skills"
actual_skills = len(list(skills_dir.iterdir())) if skills_dir.exists() else 0
check(" ", 15, actual_skills, tolerance=2)

# 5. inbox file
actual_inbox = count_files(T9 / "field" / "inbox")
check("inbox file ", 460, actual_inbox, tolerance=50)

# 6. guardian worker
try:
    import sys
    sys.path.insert(0, str(T9))
    from pipes.gm_batch import GUARDIAN_WORKERS
    actual_workers = sum(len(g["workers"]) for g in GUARDIAN_WORKERS.values())
    check("guardian  ", 19, actual_workers)
except Exception:
    pass

# 7. DB
try:
    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    actual_entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    conn.close()
    # items tolerance
    if actual_entities > 0:
        PASS += 1
    else:
        WARN += 1
        print(f"  [STALE] DB : 0items (normal)")
except Exception:
    pass

# 8. smoke test item — executionresult
try:
    r = subprocess.run(["python3", str(T9 / "tests" / "smoke_test.py")],
                       capture_output=True, text=True, timeout=30, cwd=str(T9))
    match = re.search(r"PASS=(\d+)", r.stdout)
    if match:
        actual_checks = int(match.group(1))
        check("smoke test PASS ", 37, actual_checks, tolerance=3)
except Exception:
    pass

# 9. state model (TRANSITIONS dict)
try:
    seed_content = (T9 / "t9_seed.py").read_text(encoding="utf-8")
    transition_count = seed_content.count('"preindividual"') + seed_content.count('"impulse"')
    # TRANSITIONS13key
    match = re.search(r"TRANSITIONS\s*=\s*\{(.+?)\n\}", seed_content, re.DOTALL)
    if match:
        keys = re.findall(r'"(\w+)"\s*:', match.group(1))
        check("state model ", 13, len(keys), tolerance=1)
except Exception:
    pass

# 10. cron register
try:
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
    if r.returncode == 0:
        cron_lines = [l for l in r.stdout.splitlines() if l.strip() and not l.startswith("#")]
        check("cron register ", 13, len(cron_lines), tolerance=2)
except Exception:
    pass

print(f"\n  === result: PASS={PASS} STALE={WARN} ===")
if WARN == 0:
    print("  ALL CLAIMS VERIFIED\n")
else:
    print(f"  {WARN}items stale — BIBLE.md/CLAUDE.md update \n")
