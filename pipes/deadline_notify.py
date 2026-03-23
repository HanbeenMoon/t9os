#!/usr/bin/env python3
"""T9 마감일 텔레그램 알림 — t9_seed.py daily에서 마감일을 읽는다.

기존: 노션 dump 텍스트 파일에서 파싱 (죽은 데이터)
변경: t9_seed.py daily 출력 + state.md 파싱 (라이브 데이터)
"""
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import T9, WORKSPACE
from lib.logger import pipeline_run

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tg_common import tg_send

STATE_MD = WORKSPACE / ".claude" / "state.md"
T9_SEED = T9 / "t9_seed.py"


def load_deadlines_from_seed():
    """t9_seed.py daily 출력에서 마감일 파싱."""
    try:
        result = subprocess.run(
            ["python3", str(T9_SEED), "daily"],
            capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.splitlines()
    except Exception:
        lines = []

    deadlines = []
    for line in lines:
        # "D-4    2026-03-24 프로젝트 제출 마감 *긴급*" 패턴
        m = re.match(r'\s*D-(\d+)\s+(\d{4}-\d{2}-\d{2})\s+(.+)', line)
        if m:
            delta = int(m.group(1))
            date_str = m.group(2)
            name = m.group(3).strip().rstrip('*긴급* ').strip()
            deadlines.append((delta, date_str, name))

    return sorted(deadlines)


def load_deadlines_from_state():
    """state.md에서 마감일 파싱 (백업 소스)."""
    if not STATE_MD.exists():
        return []
    content = STATE_MD.read_text(encoding="utf-8")
    deadlines = []
    today = datetime.now().date()
    for line in content.splitlines():
        # "- **D-5** 2026-03-24 프로젝트 마감" 패턴
        m = re.match(r'\s*-\s+\*\*D-(\d+)\*\*\s+(\d{4}-\d{2}-\d{2})\s+(.+)', line)
        if m:
            delta = int(m.group(1))
            name = m.group(3).strip()
            # D-N을 실제 날짜 기준으로 재계산
            date_obj = datetime.strptime(m.group(2), "%Y-%m-%d").date()
            real_delta = (date_obj - today).days
            deadlines.append((real_delta, m.group(2), name))
    return sorted(deadlines)


def notify():
    """마감일 알림 — D-7 이내만."""
    deadlines = load_deadlines_from_seed()
    if not deadlines:
        deadlines = load_deadlines_from_state()
    if not deadlines:
        return

    urgent = [d for d in deadlines if d[0] <= 7]
    if not urgent:
        return

    msg = "📅 T9 마감일 알림\n\n"
    for delta, date_str, name in urgent:
        if delta < 0:
            label = "⚠️ 지남!"
        elif delta == 0:
            label = "🔴 오늘!"
        elif delta == 1:
            label = "🟠 내일"
        elif delta <= 3:
            label = f"🟡 D-{delta}"
        else:
            label = f"D-{delta}"
        msg += f"  {label}  {date_str}  {name}\n"

    tg_send(msg)


if __name__ == "__main__":
    with pipeline_run("deadline_notify"):
        notify()
