#!/usr/bin/env python3
"""T9 CEO Brief — 의사결정 필요 사항만 텔레그램 보고.
마감일 나열이 아니라, CEO가 행동해야 할 것만 보낸다.
아무것도 없으면 보내지 않는다."""
import sys, sqlite3
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import T9, WORKSPACE, DB_PATH
from lib.logger import pipeline_run

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tg_common import tg_send


def _get_db():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def _get_deadlines():
    """state.md와 seed daily에서 마감일 추출"""
    state_path = WORKSPACE / ".claude" / "state.md"
    if not state_path.exists():
        return []
    import re
    content = state_path.read_text(encoding="utf-8", errors="replace")
    results = []
    today = datetime.now().date()
    # D-N 패턴 또는 날짜 패턴 매칭
    for line in content.split("\n"):
        # "- D-7 2026-03-24 프로젝트 마감" 패턴
        m = re.search(r'(\d{4}-\d{2}-\d{2})\s+(.+?)(?:\s$)', line)
        if m:
            try:
                d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                delta = (d - today).days
                if -3 <= delta <= 14:
                    results.append((delta, m.group(1), m.group(2).strip()))
            except ValueError:
                pass
    # seed DB의 urgency=high 엔티티에서 마감 추출
    conn = _get_db()
    if conn:
        try:
            rows = conn.execute(
                "SELECT filename, metadata FROM entities "
                "WHERE phase NOT IN ('archived','dissolved','stabilized','sediment') "
                "AND metadata LIKE '%마감%'"
            ).fetchall()
            for r in rows:
                meta = r["metadata"] or ""
                dm = re.search(r'(\d{4}-\d{2}-\d{2})', meta)
                if dm:
                    try:
                        d = datetime.strptime(dm.group(1), "%Y-%m-%d").date()
                        delta = (d - today).days
                        if -3 <= delta <= 7:
                            name = r["filename"].replace(".md", "")[:50]
                            if not any(name in x[2] for x in results):
                                results.append((delta, dm.group(1), name))
                    except ValueError:
                        pass
        except Exception:
            pass
        conn.close()
    return sorted(set(results))


def build_brief():
    now = datetime.now()
    sections = []

    # === 1. 마감 임박 (D-3 이하) — 구체적 행동 포함 ===
    deadlines = _get_deadlines()
    urgent_dl = [d for d in deadlines if d[0] <= 3]
    if urgent_dl:
        lines = ["📅 마감 임박 — 행동 필요"]
        for delta, date, title in urgent_dl:
            if delta < 0:
                label = "⚠️ 지남!"
            elif delta == 0:
                label = "🔴 오늘"
            elif delta == 1:
                label = "🟡 내일"
            else:
                label = f"D-{delta}"
            lines.append(f"  {label} {title}")
        sections.append("\n".join(lines))

    conn = _get_db()
    if not conn:
        if sections:
            return f"T9 Brief — {now:%m/%d %H:%M}\n\n" + "\n\n".join(sections)
        return None

    # === 2. 블로커 — 7일+ 정체, 결정 필요 ===
    week_ago = (now - timedelta(days=7)).isoformat()
    try:
        stale = conn.execute(
            "SELECT id, filename, phase, updated_at FROM entities "
            "WHERE phase='individuating' AND updated_at < ? "
            "ORDER BY updated_at LIMIT 5", (week_ago,)
        ).fetchall()
        if stale:
            lines = ["🚧 블로커 — 계속/중단/폐기 결정"]
            for r in stale:
                days = (now - datetime.fromisoformat(r["updated_at"])).days
                name = r["filename"].replace(".md", "")[:40]
                lines.append(f"  {name} ({days}일 정체)")
            sections.append("\n".join(lines))
    except Exception:
        pass

    # === 3. 24h 내 상태 변동 요약 ===
    yesterday = (now - timedelta(hours=24)).isoformat()
    try:
        transitions = conn.execute(
            "SELECT t.from_phase, t.to_phase, e.filename FROM transitions t "
            "JOIN entities e ON t.entity_id = e.id "
            "WHERE t.timestamp >= ? ORDER BY t.timestamp DESC LIMIT 8",
            (yesterday,)
        ).fetchall()
        if transitions:
            lines = ["🔄 24h 변동"]
            for t in transitions:
                name = t["filename"].replace(".md", "")[:35]
                lines.append(f"  {name}: {t['from_phase']}→{t['to_phase']}")
            sections.append("\n".join(lines))
    except Exception:
        pass

    # === 4. 인박스 과부하 ===
    try:
        counts = {}
        for phase in ["preindividual", "tension_detected", "individuating", "stabilized"]:
            row = conn.execute(
                "SELECT COUNT() as c FROM entities WHERE phase=?", (phase,)
            ).fetchone()
            counts[phase] = row["c"] if row else 0

        if counts["preindividual"] > 20:
            sections.append(
                f"📥 인박스 과부하\n  전개체 {counts['preindividual']}건 — "
                f"정리/tidy 필요\n  (다음 tidy: 일/수 10:00)"
            )
    except Exception:
        counts = {"preindividual": 0, "individuating": 0, "stabilized": 0}

    # === 5. 긴급 미해결 (tension_detected) ===
    try:
        tension = conn.execute(
            "SELECT id, filename FROM entities "
            "WHERE phase='tension_detected' LIMIT 5"
        ).fetchall()
        if tension:
            lines = ["🔥 긴장 감지 — 확인 필요"]
            for r in tension:
                name = r["filename"].replace(".md", "")[:40]
                lines.append(f"  [{r['id']}] {name}")
            sections.append("\n".join(lines))
    except Exception:
        pass

    conn.close()

    # === 조립 ===
    if not sections:
        return None  # 보고할 것 없음 = CEO 방해 안 함

    header = f"T9 CEO Brief — {now:%m/%d %H:%M}\n"
    ind = counts.get("individuating", 0)
    pre = counts.get("preindividual", 0)
    stab = counts.get("stabilized", 0)
    footer = f"\n_{ind} active | {pre} inbox | {stab} stabilized_"
    return header + "\n\n".join(sections) + "\n" + footer


def main():
    brief = build_brief()
    if brief:
        if "--dry-run" in sys.argv:
            print(brief)
        else:
            tg_send(brief)
            print(f"[{datetime.now():%H:%M:%S}] CEO brief sent")
    else:
        print(f"[{datetime.now():%H:%M:%S}] Nothing to report — CEO 방해 안 함")


if __name__ == "__main__":
    with pipeline_run("ceo_brief"):
        main()
