"""
Task database layer using SQLite.

Handles all persistence: create, query, update, and deadline lookups.
Designed for single-user Telegram bot with minimal overhead.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, date
from enum import StrEnum
from pathlib import Path
from typing import Generator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent / "tasks.db"

SCHEMA = """\
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    due_date    TEXT,                          -- ISO-8601 date (YYYY-MM-DD)
    priority    TEXT    NOT NULL DEFAULT 'medium',
    status      TEXT    NOT NULL DEFAULT 'todo',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
"""


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Status(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass(frozen=True, slots=True)
class Task:
    """Immutable snapshot of a task row."""

    id: int
    title: str
    due_date: date | None
    priority: Priority
    status: Status
    created_at: datetime
    updated_at: datetime

    # -- presentation helpers ------------------------------------------------

    @property
    def priority_emoji(self) -> str:
        return {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[self.priority]

    @property
    def status_emoji(self) -> str:
        return {"todo": "📋", "in_progress": "⏳", "done": "✅"}[self.status]

    def format_short(self) -> str:
        """One-line summary for Telegram messages."""
        due = f" (due {self.due_date})" if self.due_date else ""
        return f"{self.status_emoji} {self.priority_emoji} #{self.id} {self.title}{due}"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _parse_row(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        due_date=date.fromisoformat(row["due_date"]) if row["due_date"] else None,
        priority=Priority(row["priority"]),
        status=Status(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


@contextmanager
def _connect(db_path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Yield a connection with row_factory set and WAL mode enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH) -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def add_task(
    title: str,
    due_date: date | None = None,
    priority: Priority = Priority.MEDIUM,
    *,
    db_path: Path = DB_PATH,
) -> Task:
    """Insert a new task and return it."""
    now = datetime.now().isoformat()
    due_str = due_date.isoformat() if due_date else None

    with _connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title, due_date, priority, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, due_str, priority.value, Status.TODO.value, now, now),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()

    return _parse_row(row)


def get_task(task_id: int, *, db_path: Path = DB_PATH) -> Task | None:
    """Fetch a single task by ID."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _parse_row(row) if row else None


def list_tasks(
    status: Status | None = None,
    *,
    db_path: Path = DB_PATH,
) -> list[Task]:
    """Return tasks filtered by status (or all if None), ordered by due date."""
    with _connect(db_path) as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY due_date ASC NULLS LAST",
                (status.value,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY due_date ASC NULLS LAST"
            ).fetchall()

    return [_parse_row(r) for r in rows]


def complete_task(task_id: int, *, db_path: Path = DB_PATH) -> Task | None:
    """Mark a task as done. Returns updated task or None if not found."""
    now = datetime.now().isoformat()
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
            (Status.DONE.value, now, task_id),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _parse_row(row) if row else None


def get_tasks_due_by(target: date, *, db_path: Path = DB_PATH) -> list[Task]:
    """Return open tasks with due_date on or before *target*."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM tasks "
            "WHERE status != ? AND due_date IS NOT NULL AND due_date <= ? "
            "ORDER BY due_date ASC",
            (Status.DONE.value, target.isoformat()),
        ).fetchall()
    return [_parse_row(r) for r in rows]


def get_daily_summary(*, db_path: Path = DB_PATH) -> dict[str, int]:
    """Aggregate counts by status for the daily digest."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status"
        ).fetchall()
    return {row["status"]: row["cnt"] for row in rows}
