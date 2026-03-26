"""
마감 수확기 v2 — Notion 의존 완전 제거.
전개체를 "일정"이라는 위상으로 개체화하는 모듈.

Source: DB(entities.deadline_date)가 단일 소스.
- capture 시 extract_date()로 마감 자동 감지 → DB 직접 기록
- harvest_deadlines()는 기존 엔티티 본문에서 날짜 재스캔 (보조)
- Notion dump 의존 없음
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent

_DATE_ISO = re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})')
_DATE_KR = re.compile(r'(\d{1,2})월\s*(\d{1,2})일')
_DATE_DDAY = re.compile(r'D-(\d+)', re.IGNORECASE)


def extract_date(text):
    """텍스트에서 날짜 추출. 마감 키워드와 함께 있을 때만."""
    has_deadline_keyword = bool(re.search(r'마감|제출|시험|고사|deadline|due', text, re.IGNORECASE))
    if not has_deadline_keyword:
        return None

    m = _DATE_ISO.search(text)
    if m:
        try:
            d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass
    m = _DATE_KR.search(text)
    if m:
        try:
            year = datetime.now().year
            d = datetime(year, int(m.group(1)), int(m.group(2)))
            if d.date() < datetime.now().date() - timedelta(days=30):
                d = d.replace(year=year + 1)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass
    # M/D 슬래시 패턴 (4/15 등)
    m = re.search(r'(\d{1,2})/(\d{1,2})', text)
    if m:
        try:
            year = datetime.now().year
            d = datetime(year, int(m.group(1)), int(m.group(2)))
            if d.date() < datetime.now().date() - timedelta(days=30):
                d = d.replace(year=year + 1)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass
    m = _DATE_DDAY.search(text)
    if m:
        target = datetime.now() + timedelta(days=int(m.group(1)))
        return target.strftime("%Y-%m-%d")
    return None


def harvest_deadlines(conn):
    """DB 내 엔티티 본문에서 마감일 재스캔. 기존 deadline_date는 건드리지 않음.
    deadline_date가 NULL인 엔티티만 스캔해서 보충."""
    count = 0
    try:
        rows = conn.execute(
            "SELECT id, filename, body_preview FROM entities "
            "WHERE deadline_date IS NULL "
            "AND phase NOT IN ('dissolved', 'sediment') "
            "AND body_preview NOT LIKE '# CC Session%' "
            "AND filename NOT LIKE '%_brief.md' "
            "AND filename NOT LIKE '%GoogleCalendar%' "
            "AND (filename LIKE '%마감%' OR filename LIKE '%제출%' "
            "     OR filename LIKE '%시험%' OR filename LIKE '%고사%' "
            "     OR body_preview LIKE '%마감%' OR body_preview LIKE '%제출%')"
        ).fetchall()

        for row in rows:
            text = f"{row['filename']} {row['body_preview'] or ''}"
            date = extract_date(text)
            if date:
                conn.execute(
                    "UPDATE entities SET deadline_date = ? WHERE id = ?",
                    (date, row["id"])
                )
                count += 1

        if count > 0:
            conn.commit()
    except Exception:
        pass

    return count
