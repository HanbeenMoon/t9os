#!/usr/bin/env python3
"""T9 CEO Brief v5 — DB에서 마감 직접 쿼리. stdout 파싱 없음.
마감 없으면 안 보냄."""
import sys, re, sqlite3
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import T9, DB_PATH
from lib.logger import pipeline_run

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tg_common import tg_send


def build_brief():
    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row

    today = datetime.now().strftime("%Y-%m-%d")
    cutoff = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

    rows = conn.execute(
        "SELECT filename, deadline_date, urgency, metadata FROM entities "
        "WHERE deadline_date IS NOT NULL "
        "AND deadline_date >= ? AND deadline_date <= ? "
        "AND phase NOT IN ('dissolved', 'sediment') "
        "ORDER BY deadline_date",
        (today, cutoff)
    ).fetchall()
    conn.close()

    if not rows:
        return None

    lines = []
    for r in rows:
        delta = (datetime.strptime(r["deadline_date"], "%Y-%m-%d").date() - datetime.now().date()).days
        if delta == 0:
            label = "오늘"
        elif delta == 1:
            label = "내일"
        else:
            label = f"D-{delta}"

        # display_title 있으면 그걸 사용 (AI 정제된 제목)
        name = None
        try:
            import json
            meta = json.loads(r["metadata"]) if r["metadata"] else {}
            name = meta.get("display_title")
        except Exception:
            pass

        if not name:
            name = r["filename"].replace(".md", "")
            name = re.sub(r'^\d{8}_?', '', name)
            name = re.sub(r'^마감_', '', name)
            name = re.sub(r'SC41 마감 ', '', name)
            name = re.sub(r'_?\d{3,8}$', '', name)
            name = re.sub(r'\s*\d{8,}', '', name)
            name = re.sub(r'\s+\d{2,4}$', '', name)  # 끝에 남은 숫자 잔해
            name = name.replace("_", " ").strip()[:40]

        # 긴급도 이모지
        if delta == 0:
            emoji = "🔴"
        elif delta <= 3:
            emoji = "🟡"
        else:
            emoji = "⚪"

        lines.append(f"{emoji} {label}  {name}")

    header = f"📋 T9 마감 브리프 ({datetime.now():%m/%d %H:%M})"
    return header + "\n\n" + "\n".join(lines)


def main():
    brief = build_brief()
    if brief:
        if "--dry-run" in sys.argv:
            print(brief)
        else:
            tg_send(brief)
            print(f"[{datetime.now():%H:%M:%S}] sent")
    else:
        print(f"[{datetime.now():%H:%M:%S}] no deadlines")


if __name__ == "__main__":
    with pipeline_run("ceo_brief"):
        main()
