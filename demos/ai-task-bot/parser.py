"""
Natural-language intent parser for task commands.

Two backends available:
  1. Regex-based (default) -- zero dependencies, works offline
  2. Claude API           -- set ANTHROPIC_API_KEY to enable

The regex parser handles common Korean & English patterns:
  "내일까지 보고서 제출"       -> add(title="보고서 제출", due=tomorrow)
  "add report by Friday"     -> add(title="report", due=friday)
  "complete #3"              -> complete(task_id=3)
  "show tasks"               -> list()
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum
from typing import Any

from db import Priority


# ---------------------------------------------------------------------------
# Intent types
# ---------------------------------------------------------------------------

class Intent(StrEnum):
    ADD = "add"
    LIST = "list"
    COMPLETE = "complete"
    HELP = "help"
    SUMMARY = "summary"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ParseResult:
    """Structured output from the parser."""

    intent: Intent
    title: str = ""
    due_date: date | None = None
    priority: Priority = Priority.MEDIUM
    task_id: int | None = None
    confidence: float = 1.0              # 0-1, useful when AI backend is active
    raw_text: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Date resolution helpers
# ---------------------------------------------------------------------------

_KO_RELATIVE: dict[str, int] = {
    "오늘": 0, "내일": 1, "모레": 2, "글피": 3,
    "이번주": 0, "다음주": 7,
}

_EN_RELATIVE: dict[str, int] = {
    "today": 0, "tomorrow": 1, "day after tomorrow": 2,
}

_EN_WEEKDAYS: dict[str, int] = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _resolve_date(text: str) -> date | None:
    """Try to extract a date from natural-language text."""
    lower = text.lower().strip()
    today = date.today()

    # Korean relative dates: 내일까지, 모레까지, etc.
    for token, delta in _KO_RELATIVE.items():
        if token in text:
            return today + timedelta(days=delta)

    # English relative dates
    for token, delta in _EN_RELATIVE.items():
        if token in lower:
            return today + timedelta(days=delta)

    # English weekday: "by Friday"
    for day_name, weekday_num in _EN_WEEKDAYS.items():
        if day_name in lower:
            days_ahead = (weekday_num - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7          # next occurrence
            return today + timedelta(days=days_ahead)

    # Explicit ISO date: 2026-04-01
    iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if iso_match:
        try:
            return date.fromisoformat(iso_match.group(1))
        except ValueError:
            pass

    # Compact date: 4/1, 04-01  (assume current year)
    compact = re.search(r"(\d{1,2})[/-](\d{1,2})", text)
    if compact:
        try:
            return date(today.year, int(compact.group(1)), int(compact.group(2)))
        except ValueError:
            pass

    return None


def _resolve_priority(text: str) -> Priority:
    """Detect priority keywords."""
    lower = text.lower()
    if any(k in lower for k in ("urgent", "긴급", "asap", "급한")):
        return Priority.URGENT
    if any(k in lower for k in ("high", "높은", "중요")):
        return Priority.HIGH
    if any(k in lower for k in ("low", "낮은", "나중")):
        return Priority.LOW
    return Priority.MEDIUM


# ---------------------------------------------------------------------------
# Regex-based parser
# ---------------------------------------------------------------------------

# Patterns grouped by intent

_ADD_PATTERNS: list[re.Pattern[str]] = [
    # Korean: "내일까지 보고서 제출", "보고서 제출 추가"
    re.compile(r"(?:추가|등록|만들어|생성|할일)\s*[:：]?\s*(.+)", re.IGNORECASE),
    re.compile(r"(.+?)\s*(?:추가|등록|해줘|해 줘|만들어)", re.IGNORECASE),
    # Korean: sentences ending with ~까지 imply a task
    re.compile(r"(.+까지\s+.+)"),
    # English: "add ...", "create ...", "new task ..."
    re.compile(r"(?:add|create|new task|remind me to)\s+(.+)", re.IGNORECASE),
]

_COMPLETE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:완료|끝|done|complete|finish)\s*#?(\d+)", re.IGNORECASE),
    re.compile(r"#(\d+)\s*(?:완료|끝|done|complete)", re.IGNORECASE),
]

_LIST_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:목록|리스트|보여|조회|show|list|tasks|할일)", re.IGNORECASE),
]

_SUMMARY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:요약|summary|daily|오늘|브리핑|briefing|digest)", re.IGNORECASE),
]

_HELP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:help|도움|사용법|명령어|/help|/start)", re.IGNORECASE),
]


def _clean_title(raw: str) -> str:
    """Strip date/priority noise from the extracted title."""
    title = raw.strip()
    # Remove trailing particles: 까지, by Friday, etc.
    title = re.sub(r"\s*(?:까지|by\s+\S+)\s*$", "", title, flags=re.IGNORECASE)
    # Remove leading date tokens that leaked in
    for token in list(_KO_RELATIVE.keys()) + list(_EN_RELATIVE.keys()):
        title = re.sub(rf"^{re.escape(token)}\s*", "", title, flags=re.IGNORECASE)
    # Remove priority keywords
    for kw in ("urgent", "긴급", "high", "중요", "low", "낮은"):
        title = re.sub(rf"\b{re.escape(kw)}\b", "", title, flags=re.IGNORECASE)
    return title.strip(" ,.:;!") or raw.strip()


def parse_regex(text: str) -> ParseResult:
    """Parse user message using regex heuristics."""

    # -- complete --------------------------------------------------------
    for pat in _COMPLETE_PATTERNS:
        m = pat.search(text)
        if m:
            return ParseResult(
                intent=Intent.COMPLETE,
                task_id=int(m.group(1)),
                raw_text=text,
            )

    # -- help ------------------------------------------------------------
    for pat in _HELP_PATTERNS:
        if pat.search(text):
            return ParseResult(intent=Intent.HELP, raw_text=text)

    # -- summary ---------------------------------------------------------
    for pat in _SUMMARY_PATTERNS:
        if pat.search(text):
            return ParseResult(intent=Intent.SUMMARY, raw_text=text)

    # -- list ------------------------------------------------------------
    for pat in _LIST_PATTERNS:
        if pat.search(text):
            return ParseResult(intent=Intent.LIST, raw_text=text)

    # -- add (must come last — broadest patterns) ------------------------
    for pat in _ADD_PATTERNS:
        m = pat.search(text)
        if m:
            raw_title = m.group(1)
            return ParseResult(
                intent=Intent.ADD,
                title=_clean_title(raw_title),
                due_date=_resolve_date(text),
                priority=_resolve_priority(text),
                raw_text=text,
            )

    # -- fallback: treat any non-trivial text as implicit add ------------
    if len(text.strip()) > 2:
        return ParseResult(
            intent=Intent.ADD,
            title=_clean_title(text),
            due_date=_resolve_date(text),
            priority=_resolve_priority(text),
            confidence=0.6,
            raw_text=text,
        )

    return ParseResult(intent=Intent.UNKNOWN, raw_text=text)


# ---------------------------------------------------------------------------
# Claude API parser (optional upgrade)
# ---------------------------------------------------------------------------

def parse_ai(text: str) -> ParseResult:
    """
    Use Claude API for intent classification and entity extraction.

    Requires ANTHROPIC_API_KEY in the environment.
    Falls back to regex parser if the key is missing or the call fails.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return parse_regex(text)

    try:
        import anthropic  # type: ignore[import-untyped]

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            system=(
                "You are a task-management intent parser. "
                "Given a user message, return JSON with keys: "
                "intent (add|list|complete|summary|help|unknown), "
                "title (string), due_date (YYYY-MM-DD or null), "
                "priority (low|medium|high|urgent), task_id (int or null). "
                "Respond ONLY with valid JSON, no markdown."
            ),
            messages=[{"role": "user", "content": text}],
        )

        data = json.loads(response.content[0].text)
        return ParseResult(
            intent=Intent(data.get("intent", "unknown")),
            title=data.get("title", ""),
            due_date=date.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            priority=Priority(data.get("priority", "medium")),
            task_id=data.get("task_id"),
            confidence=0.95,
            raw_text=text,
        )

    except Exception:
        # Any failure -> graceful fallback to regex
        return parse_regex(text)


# ---------------------------------------------------------------------------
# Public API: auto-select backend
# ---------------------------------------------------------------------------

def parse(text: str) -> ParseResult:
    """
    Parse a user message into a structured intent.

    Uses Claude API if ANTHROPIC_API_KEY is set, otherwise regex.
    """
    if os.getenv("ANTHROPIC_API_KEY"):
        return parse_ai(text)
    return parse_regex(text)
