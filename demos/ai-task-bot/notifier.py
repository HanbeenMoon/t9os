"""
Deadline notification engine.

Can run in two modes:
  1. Standalone (cron)  -- `python notifier.py` sends alerts via Telegram
  2. Imported            -- bot.py calls check_and_notify() on schedule

Notification rules:
  - Overdue tasks  -> immediate alert
  - Due today      -> morning reminder
  - Due tomorrow   -> evening heads-up
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, timedelta

from db import DB_PATH, Task, get_daily_summary, get_tasks_due_by, init_db, list_tasks, Status

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------

def _format_overdue(tasks: list[Task]) -> str:
    if not tasks:
        return ""
    lines = ["🚨 *Overdue Tasks*\n"]
    for t in tasks:
        days = (date.today() - t.due_date).days if t.due_date else 0
        lines.append(f"  {t.format_short()}  — {days}d overdue")
    return "\n".join(lines)


def _format_due_today(tasks: list[Task]) -> str:
    if not tasks:
        return ""
    lines = ["📅 *Due Today*\n"]
    for t in tasks:
        lines.append(f"  {t.format_short()}")
    return "\n".join(lines)


def _format_due_tomorrow(tasks: list[Task]) -> str:
    if not tasks:
        return ""
    lines = ["🔔 *Due Tomorrow*\n"]
    for t in tasks:
        lines.append(f"  {t.format_short()}")
    return "\n".join(lines)


def _format_daily_digest() -> str:
    """Build a daily summary message."""
    summary = get_daily_summary()
    total = sum(summary.values())
    todo = summary.get("todo", 0)
    in_progress = summary.get("in_progress", 0)
    done = summary.get("done", 0)

    # Upcoming deadlines (next 7 days)
    upcoming = get_tasks_due_by(date.today() + timedelta(days=7))
    open_upcoming = [t for t in upcoming if t.status != Status.DONE]

    lines = [
        "📊 *Daily Task Summary*\n",
        f"Total: {total}  |  📋 {todo}  ⏳ {in_progress}  ✅ {done}",
    ]

    if open_upcoming:
        lines.append(f"\n🗓 *Next 7 days* ({len(open_upcoming)} tasks):")
        for t in open_upcoming[:10]:
            lines.append(f"  {t.format_short()}")

    active = list_tasks(Status.IN_PROGRESS)
    if active:
        lines.append(f"\n⏳ *In Progress* ({len(active)}):")
        for t in active[:5]:
            lines.append(f"  {t.format_short()}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Notification dispatcher
# ---------------------------------------------------------------------------

def build_notification() -> str:
    """
    Build the full notification message.

    Returns an empty string if there's nothing to report.
    """
    today = date.today()
    tomorrow = today + timedelta(days=1)

    all_due = get_tasks_due_by(tomorrow)
    overdue = [t for t in all_due if t.due_date and t.due_date < today]
    due_today = [t for t in all_due if t.due_date == today]
    due_tomorrow = [t for t in all_due if t.due_date == tomorrow]

    sections = [
        _format_overdue(overdue),
        _format_due_today(due_today),
        _format_due_tomorrow(due_tomorrow),
    ]

    # Filter empty sections and join
    message = "\n\n".join(s for s in sections if s)
    return message


def build_daily_digest() -> str:
    """Build the daily digest message."""
    return _format_daily_digest()


async def send_telegram(text: str, *, chat_id: str, token: str) -> bool:
    """
    Send a message via Telegram Bot API.

    Returns True on success, False on failure.
    """
    if not text.strip():
        logger.info("Nothing to send — no pending notifications.")
        return True

    try:
        from telegram import Bot  # type: ignore[import-untyped]

        bot = Bot(token=token)
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
        )
        logger.info("Notification sent to chat %s", chat_id)
        return True

    except Exception as e:
        logger.error("Failed to send notification: %s", e)
        return False


async def check_and_notify() -> None:
    """
    Main entry point: check deadlines and send notifications.

    Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from environment.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        logger.warning(
            "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. "
            "Printing notification to stdout instead."
        )
        notification = build_notification()
        if notification:
            print(notification)
        else:
            print("No pending notifications.")
        return

    notification = build_notification()
    await send_telegram(notification, chat_id=chat_id, token=token)


async def send_daily_digest() -> None:
    """Send the daily digest. Called by cron or the bot's scheduler."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    digest = build_daily_digest()

    if not token or not chat_id:
        print(digest)
        return

    await send_telegram(digest, chat_id=chat_id, token=token)


# ---------------------------------------------------------------------------
# CLI entry point (for cron)
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Run as standalone script for cron integration.

    Example crontab entries:
        # Deadline alerts every 2 hours (9am-9pm)
        0 9-21/2 * * * cd /path/to/ai-task-bot && python notifier.py --check

        # Daily digest at 8am
        0 8 * * * cd /path/to/ai-task-bot && python notifier.py --digest
    """
    import argparse

    arg_parser = argparse.ArgumentParser(description="Task deadline notifier")
    arg_parser.add_argument(
        "--digest", action="store_true", help="Send daily digest instead of deadline alerts"
    )
    arg_parser.add_argument(
        "--check", action="store_true", default=True, help="Check deadlines (default)"
    )
    args = arg_parser.parse_args()

    init_db()

    if args.digest:
        asyncio.run(send_daily_digest())
    else:
        asyncio.run(check_and_notify())


if __name__ == "__main__":
    main()
