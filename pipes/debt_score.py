#!/usr/bin/env python3
"""부채 점수 측정 — EU ETS 모델.
세션 간 책임 불연속 해결: 미래 비용을 현재에 가시화."""
import subprocess, sys
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent
HANBEEN = T9.parent

def count_todos():
    """TODO/FIXME/HACK 건수"""
    try:
        r = subprocess.run(
            ["grep", "-r", "--include=*.py", "--include=*.sh", "--include=*.md",
             "-c", "-E", "TODO|FIXME|HACK|XXX",
             str(T9 / "pipes"), str(T9 / "lib"), str(T9 / "t9_seed.py")],
            capture_output=True, text=True, timeout=10
        )
        total = sum(int(line.split(":")[-1]) for line in r.stdout.strip().splitlines() if ":" in line)
        return total
    except Exception:
        return 0

def count_duplicates():
    """함수 중복 (간이 탐지: 동일 함수명이 2+ 파일에)"""
    try:
        r = subprocess.run(
            ["grep", "-rn", "--include=*.py", "^def ",
             str(T9 / "pipes"), str(T9 / "lib"), str(T9 / "t9_seed.py")],
            capture_output=True, text=True, timeout=10
        )
        funcs = {}
        for line in r.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 3:
                fname = parts[2].strip().split("(")[0].replace("def ", "")
                if fname.startswith("_") or fname in ("main", "cli"):
                    continue
                funcs.setdefault(fname, []).append(parts[0])
        dupes = {k: v for k, v in funcs.items() if len(v) > 1}
        return len(dupes), dupes
    except Exception:
        return 0, {}

def smoke_test_failures():
    """smoke test 실패 건수"""
    try:
        r = subprocess.run(
            ["python3", str(T9 / "tests" / "smoke_test.py")],
            capture_output=True, text=True, timeout=30, cwd=str(T9)
        )
        fail_count = r.stdout.count("FAIL")
        return fail_count
    except Exception:
        return -1  # 실행 실패

def check_db_hardcoding():
    """DB 경로 하드코딩 건수 (config.py 경유하지 않는 것)"""
    try:
        r = subprocess.run(
            ["grep", "-rn", "--include=*.py", r"sqlite3\.connect",
             str(T9 / "pipes"), str(T9 / "lib"), str(T9 / "mcp")],
            capture_output=True, text=True, timeout=10
        )
        violations = []
        for line in r.stdout.strip().splitlines():
            path = line.split(":")[0]
            # config.py, ipc.py, t9_seed.py는 정당한 DB 접근
            if any(ok in path for ok in ["config.py", "ipc.py", "t9_seed.py", "test", "smoke", "migration"]):
                continue
            violations.append(path)
        return len(set(violations)), list(set(violations))
    except Exception:
        return 0, []

def main():
    score = 0
    details = []

    # 1. TODO/FIXME/HACK
    todos = count_todos()
    score += todos * 1
    details.append(f"  TODO/FIXME/HACK: {todos}건 (+{todos}점)")

    # 2. 함수 중복
    dupe_count, dupes = count_duplicates()
    score += dupe_count * 5
    details.append(f"  함수 중복: {dupe_count}건 (+{dupe_count * 5}점)")
    for fname, files in list(dupes.items())[:3]:
        details.append(f"    {fname}: {len(files)}곳")

    # 3. smoke test
    fails = smoke_test_failures()
    if fails > 0:
        score += fails * 20
        details.append(f"  smoke test 실패: {fails}건 (+{fails * 20}점)")
    elif fails == 0:
        details.append(f"  smoke test: ALL PASS")
    else:
        details.append(f"  smoke test: 실행 실패")

    # 4. DB 하드코딩
    db_count, db_violations = check_db_hardcoding()
    score += db_count * 10
    details.append(f"  DB 하드코딩: {db_count}건 (+{db_count * 10}점)")

    # 출력
    if score <= 20:
        status = "🟢 건강"
    elif score <= 50:
        status = "🟡 주의"
    else:
        status = "🔴 위험"

    print(f"부채 점수: {score}점 {status}")
    for d in details:
        print(d)

    # 이력 기록
    history = T9 / "data" / "debt_history.log"
    history.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    with open(history, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {score}\n")

    return score

if __name__ == "__main__":
    score = main()
    sys.exit(0 if score <= 50 else 1)
