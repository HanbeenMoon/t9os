#!/usr/bin/env python3
"""
T9 OS Overnight System (TD-009)
매일 04:00 cron 실행. reindex + orphans 감지 + FTS rebuild + 장기 tension 보고.
결과를 텔레그램으로 발송.
"""
import sys, os
from pathlib import Path
from datetime import datetime, timedelta

# 경로 설정
PIPES = Path(__file__).resolve().parent
T9 = PIPES.parent
sys.path.insert(0, str(T9))
sys.path.insert(0, str(PIPES))

from lib.config import DB_PATH
from tg_common import tg_send
import sqlite3


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def run_reindex():
    """reindex 실행, 결과 카운트 반환."""
    from t9_seed import cmd_reindex
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_reindex()
    output = buf.getvalue()
    return output.strip()


def run_orphans():
    """고아 엔티티 감지 (fix 아님, 보고만)."""
    from lib.commands_ext import cmd_orphans
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_orphans(get_db, fix=False)
    output = buf.getvalue()
    return output.strip()


def run_rebuild_fts():
    """FTS5 인덱스 재구축."""
    from lib.commands_ext import cmd_rebuild_fts
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_rebuild_fts(get_db)
    output = buf.getvalue()
    return output.strip()


def find_stale_tensions(days=30):
    """30일 이상 tension 상태(preindividual/tension_detected)인 전개체 보고."""
    conn = get_db()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    rows = conn.execute("""
        SELECT id, filename, phase, updated_at, filepath
        FROM entities
        WHERE phase IN ('preindividual', 'tension_detected')
          AND updated_at < ?
        ORDER BY updated_at ASC
    """, (cutoff,)).fetchall()
    conn.close()

    if not rows:
        return f"장기 tension (>{days}일): 없음"

    lines = [f"장기 tension (>{days}일): {len(rows)}건"]
    for r in rows[:20]:  # 최대 20건만 보고
        age = (datetime.now() - datetime.fromisoformat(r["updated_at"])).days
        lines.append(f"  [{r['id']}] {r['filename']} ({r['phase']}, {age}일)")
    if len(rows) > 20:
        lines.append(f"  ... 외 {len(rows) - 20}건")
    return "\n".join(lines)


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    results = [f"[T9 Overnight] {ts}", "=" * 30]

    # 1. reindex
    try:
        out = run_reindex()
        results.append(f"[reindex] {out or 'OK'}")
    except Exception as e:
        results.append(f"[reindex] ERROR: {e}")

    # 2. orphans 감지
    try:
        out = run_orphans()
        results.append(f"[orphans] {out or '고아 없음'}")
    except Exception as e:
        results.append(f"[orphans] ERROR: {e}")

    # 3. FTS5 rebuild
    try:
        out = run_rebuild_fts()
        results.append(f"[FTS5] {out or 'OK'}")
    except Exception as e:
        results.append(f"[FTS5] ERROR: {e}")

    # 4. 장기 tension 보고
    try:
        out = find_stale_tensions(30)
        results.append(f"[tension] {out}")
    except Exception as e:
        results.append(f"[tension] ERROR: {e}")

    # 5. 엔티티 총 현황
    try:
        conn = get_db()
        total = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        phases = conn.execute("""
            SELECT phase, COUNT(*) as cnt FROM entities
            GROUP BY phase ORDER BY cnt DESC
        """).fetchall()
        conn.close()
        phase_str = ", ".join(f"{r['phase']}:{r['cnt']}" for r in phases)
        results.append(f"[총현황] {total}건 ({phase_str})")
    except Exception as e:
        results.append(f"[총현황] ERROR: {e}")

    report = "\n".join(results)
    print(report)

    # 텔레그램 발송
    try:
        tg_send(report)
    except Exception as e:
        print(f"[TG 발송 실패] {e}")


if __name__ == "__main__":
    main()
