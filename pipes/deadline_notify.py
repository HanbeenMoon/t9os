#!/usr/bin/env python3
"""T9 마감일 텔레그램 알림 — DB 직접 쿼리. D-7 이내만.
마감 없으면 안 보냄."""
import re
import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import DB_PATH
from lib.logger import pipeline_run

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tg_common import tg_send


def _clean_name(filename):
    name = filename.replace(".md", "")
    name = re.sub(r'^\d{8}_?', '', name)
    name = re.sub(r'^마감_', '', name)
    name = re.sub(r'SC41 마감 ', '', name)
    name = re.sub(r'_?\d{6}$', '', name)
    name = re.sub(r'\s*\d{8,}', '', name)
    return name.replace("_", " ").strip()[:40]


def notify():
    if not DB_PATH.exists():
        return

    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row

    today = datetime.now().strftime("%Y-%m-%d")
    cutoff = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    rows = conn.execute(
        "SELECT filename, deadline_date FROM entities "
        "WHERE deadline_date IS NOT NULL "
        "AND deadline_date >= ? AND deadline_date <= ? "
        "AND phase NOT IN ('dissolved', 'sediment') "
        "ORDER BY deadline_date",
        (today, cutoff)
    ).fetchall()
    conn.close()

    if not rows:
        return

    lines = []
    for r in rows:
        delta = (datetime.strptime(r["deadline_date"], "%Y-%m-%d").date() - datetime.now().date()).days
        if delta == 0:
            label = "오늘"
        elif delta == 1:
            label = "내일"
        else:
            label = f"D-{delta}"
        lines.append(f"{label} {_clean_name(r['filename'])}")

    tg_send("\n".join(lines))


if __name__ == "__main__":
    with pipeline_run("deadline_notify"):
        notify()
