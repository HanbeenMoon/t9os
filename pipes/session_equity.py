#!/usr/bin/env python3
"""세션 지분 시스템 (Session Equity) — 보이지 않는 손.
세션이 Task의 주주가 된다. 기여 = 지분. 상속 = 유산.

사용법:
  python3 session_equity.py compute <session_id>   # 세션 종료 시 지분 계산
  python3 session_equity.py show-recent             # 최근 세션 지분 표시
  python3 session_equity.py history                 # 지분 이력
"""
import sys, json, subprocess, re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

T9 = Path(__file__).resolve().parent.parent
HANBEEN = T9.parent
EQUITY_LOG = T9 / "data" / "equity_history.log"
BRIEFS_DIR = HANBEEN / ".claude" / "session-briefs"

# 구체화 v2: DB 접근은 lib/ipc.py의 _db()로 수렴
from lib.ipc import _db


def compute(session_id):
    """4축 기여 점수 계산 + DB 기록"""
    conn = _db()

    # 세션 정보
    session = conn.execute(
        "SELECT started_at, ended_at FROM sessions WHERE id=?", (session_id,)
    ).fetchone()
    started = session[0] if session else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ended = session[1] if session and session[1] else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 세션 지속 시간 (먼저 계산 — 짧은 세션 필터링에 필요)
    duration = 0
    try:
        t1 = datetime.strptime(started, "%Y-%m-%d %H:%M:%S")
        t2 = datetime.strptime(ended, "%Y-%m-%d %H:%M:%S")
        duration = int((t2 - t1).total_seconds() / 60)
    except Exception:
        pass

    # 10분 미만 세션은 자동 프로세스 — 기록 안 함
    if duration < 10:
        print(f"  세션 {session_id[:16]}: {duration}분 — 자동 프로세스, 지분 미기록")
        conn.close()
        return 0

    # 축1: 엔티티 창조
    entities = conn.execute(
        "SELECT COUNT(*) FROM entities WHERE created_at >= ? AND created_at <= ?",
        (started, ended)
    ).fetchone()[0]
    score_entities = entities * 10

    # 축2: 파일 변경 (git diff)
    files_modified = 0
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=str(HANBEEN)
        )
        files_modified = len([l for l in r.stdout.strip().splitlines() if l.strip()])
    except Exception:
        pass
    score_files = files_modified * 3

    # 축3: 부채 감소
    debt_reduced = 0.0
    try:
        log = T9 / "data" / "debt_history.log"
        if log.exists():
            lines = log.read_text().strip().splitlines()
            if len(lines) >= 2:
                prev = float(lines[-2].split()[-1])
                curr = float(lines[-1].split()[-1])
                debt_reduced = max(0, prev - curr)
    except Exception:
        pass
    score_debt = debt_reduced * 2

    # 축4: 한빈 만족도 (session-briefs)
    satisfaction = 0.0
    corrections = 0
    decisions = 0
    tone = "중립"
    try:
        briefs = sorted(BRIEFS_DIR.glob("*.md"), reverse=True)
        if briefs:
            brief_text = briefs[0].read_text(encoding="utf-8", errors="replace")
            # 교정 수 (감점)
            m = re.search(r'교정/피드백 (\d+)건', brief_text)
            if m:
                corrections = int(m.group(1))
            # 결정 수 (가점)
            m = re.search(r'주요 결정 (\d+)건', brief_text)
            if m:
                decisions = int(m.group(1))
            # 톤
            if '불만' in brief_text:
                tone = "불만"
            elif '긍정' in brief_text:
                tone = "긍정"
            satisfaction = (decisions * 5) - (corrections * 3) + (10 if tone == "긍정" else -10 if tone == "불만" else 0)
    except Exception:
        pass

    # 축5: IPC 협력 보상 (directive 이행/거부)
    score_cooperation = 0
    try:
        ipc_inbox = T9 / "data" / "ipc" / "inbox"
        if ipc_inbox.exists():
            short_sid = session_id[:8]
            for f in ipc_inbox.glob("*.md"):
                content = f.read_text(encoding="utf-8", errors="replace")
                # 이 세션이 이행한 directive
                if f"to: {session_id}" in content or f"to: {short_sid}" in content:
                    if "type: dispatch" in content or "type: directive" in content:
                        score_cooperation += 30  # 이행 보상
                # 이 세션이 발동한 veto (감시단 승인)
                if f"from: {session_id}" in content or f"from: {short_sid}" in content:
                    if "type: veto" in content:
                        score_cooperation += 50  # 품질 기여
    except Exception:
        pass

    # 최종 지분
    equity = score_entities + score_files + score_debt + satisfaction + score_cooperation

    # WORKING.md에서 R 섹션 추출 (상속)
    recommendation = ""
    blockers = ""
    working = HANBEEN / ".claude" / "WORKING.md"
    if working.exists():
        text = working.read_text(encoding="utf-8", errors="replace")
        r_match = re.search(r'## R .*?\n(.*?)(?=\n## |\Z)', text, re.DOTALL)
        if r_match:
            recommendation = r_match.group(1).strip()[:500]
        b_match = re.search(r'블로커|blocker', text, re.IGNORECASE)
        if b_match:
            blockers = text[b_match.start():b_match.start()+200].strip()

    # DB 기록
    conn.execute("""INSERT OR REPLACE INTO session_equity
        (session_id, started_at, ended_at, duration_minutes,
         entities_created, files_modified, debt_reduced, user_satisfaction,
         equity_score, recommendation, blockers)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (session_id, started, ended, duration,
         entities, files_modified, debt_reduced, satisfaction,
         equity, recommendation, blockers))
    conn.commit()

    # 이력 기록
    EQUITY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(EQUITY_LOG, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {session_id[:16]} {equity:.0f}\n")

    # 출력
    print(f"  세션 지분: {equity:.0f}점")
    print(f"    엔티티 창조: {entities}건 (+{score_entities})")
    print(f"    파일 변경: {files_modified}건 (+{score_files})")
    print(f"    부채 감소: {debt_reduced:.0f} (+{score_debt:.0f})")
    print(f"    만족도: 결정{decisions} 교정{corrections} 톤:{tone} ({satisfaction:+.0f})")
    print(f"    지속: {duration}분")

    conn.close()
    return equity


def show_recent(n=3):
    """최근 N개 세션 지분 표시"""
    conn = _db()
    rows = conn.execute("""
        SELECT session_id, equity_score, entities_created, files_modified,
               debt_reduced, user_satisfaction, recommendation, duration_minutes
        FROM session_equity ORDER BY started_at DESC LIMIT ?
    """, (n,)).fetchall()

    if not rows:
        print("  세션 지분 이력 없음 (첫 세션)")
        conn.close()
        return

    total = sum(r[1] for r in rows)
    print(f"  최근 {len(rows)}개 세션 총 지분: {total:.0f}점")
    for r in rows:
        sid = r[0][:16] if r[0] else "?"
        eq = r[1]
        ent = r[2]
        files = r[3]
        dur = r[7] or 0
        emoji = "🟢" if eq >= 100 else "🟡" if eq >= 30 else "🔴"
        print(f"    {emoji} [{sid}] {eq:.0f}점 (엔티티{ent} 파일{files} {dur}분)")

    # 가장 최근 세션의 권장사항
    latest = rows[0]
    if latest[6]:
        print(f"  📌 이전 세션 권장: {latest[6][:100]}")

    conn.close()


def history():
    """지분 이력"""
    if EQUITY_LOG.exists():
        lines = EQUITY_LOG.read_text().strip().splitlines()
        print(f"  지분 이력 ({len(lines)}건):")
        for line in lines[-10:]:
            print(f"    {line}")
    else:
        print("  이력 없음")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: session_equity.py compute|show-recent|history [args]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "compute" and len(sys.argv) >= 3:
        compute(sys.argv[2])
    elif cmd == "show-recent":
        show_recent()
    elif cmd == "history":
        history()
    else:
        print(f"알 수 없는 명령: {cmd}")
        sys.exit(1)
