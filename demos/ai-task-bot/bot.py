"""
AI Task Bot — Telegram bot for natural-language task management.

Architecture:
    User message → parser.parse() → intent routing → db operations → response

Built with patterns from T9OS, a personal AI operating system
managing 18 production pipelines.

Usage:
    export TELEGRAM_BOT_TOKEN="your-token-here"
    export TELEGRAM_CHAT_ID="your-chat-id"       # optional, for notifications
    export ANTHROPIC_API_KEY="sk-..."             # optional, enables AI parsing
    python bot.py
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import time as dt_time

from telegram import Update  # type: ignore[import-untyped]
from telegram.ext import (  # type: ignore[import-untyped]
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from db import (
    add_task,
    complete_task,
    get_task,
    init_db,
    list_tasks,
    Status,
)
from notifier import build_daily_digest, build_notification
from parser import Intent, parse

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai-task-bot")


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

HELP_TEXT = """\
🤖 *AI Task Bot*

Manage your tasks with natural language — Korean or English.

*Add a task:*
  "내일까지 보고서 제출"
  "add report by Friday"
  "긴급 서버 점검"

*Complete a task:*
  "완료 #3"
  "complete #5"

*View tasks:*
  "목록" / "list" / "show tasks"

*Daily summary:*
  "요약" / "summary"

*Commands:*
  /help — show this message
  /list — show all open tasks
  /summary — daily digest

Priority is auto-detected from keywords:
  🔴 urgent/긴급  🟠 high/중요  🟡 medium  🟢 low/나중
"""


def _response_add(title: str, due: str | None, priority: str, task_id: int) -> str:
    due_text = f"\n📅 Due: {due}" if due else ""
    return (
        f"✅ Task added!\n\n"
        f"*#{task_id}* {title}{due_text}\n"
        f"Priority: {priority}"
    )


def _response_complete(task_id: int, title: str) -> str:
    return f"✅ Done! *#{task_id}* ~~{title}~~ marked as complete."


def _response_list(tasks: list) -> str:
    if not tasks:
        return "📋 No open tasks. You're all caught up!"
    lines = ["📋 *Open Tasks*\n"]
    for t in tasks:
        lines.append(t.format_short())
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process any text message through the intent parser."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    result = parse(text)

    logger.info(
        "Parsed: intent=%s title=%r due=%s priority=%s confidence=%.2f",
        result.intent, result.title, result.due_date, result.priority, result.confidence,
    )

    match result.intent:
        case Intent.ADD:
            task = add_task(
                title=result.title,
                due_date=result.due_date,
                priority=result.priority,
            )
            due_str = str(task.due_date) if task.due_date else None
            response = _response_add(task.title, due_str, task.priority.value, task.id)

        case Intent.COMPLETE:
            if result.task_id is None:
                response = "Please specify a task ID, e.g. 'complete #3'"
            else:
                task = complete_task(result.task_id)
                if task:
                    response = _response_complete(task.id, task.title)
                else:
                    response = f"Task #{result.task_id} not found."

        case Intent.LIST:
            open_tasks = list_tasks(Status.TODO) + list_tasks(Status.IN_PROGRESS)
            response = _response_list(open_tasks)

        case Intent.SUMMARY:
            response = build_daily_digest()

        case Intent.HELP:
            response = HELP_TEXT

        case Intent.UNKNOWN:
            response = (
                "I'm not sure what you mean. "
                "Try 'help' to see available commands."
            )

        case _:
            response = "Something went wrong. Try again?"

    await update.message.reply_text(response, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help and /start commands."""
    if update.message:
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list command."""
    if update.message:
        open_tasks = list_tasks(Status.TODO) + list_tasks(Status.IN_PROGRESS)
        await update.message.reply_text(_response_list(open_tasks), parse_mode="Markdown")


async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /summary command."""
    if update.message:
        await update.message.reply_text(build_daily_digest(), parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Scheduled jobs
# ---------------------------------------------------------------------------

async def scheduled_deadline_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic deadline check — sends alerts to the configured chat."""
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        return

    notification = build_notification()
    if notification:
        await context.bot.send_message(
            chat_id=int(chat_id),
            text=notification,
            parse_mode="Markdown",
        )


async def scheduled_daily_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Daily digest — fires once per day at the configured time."""
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        return

    digest = build_daily_digest()
    await context.bot.send_message(
        chat_id=int(chat_id),
        text=digest,
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

def create_app(token: str) -> Application:
    """
    Build and configure the Telegram bot application.

    Registers handlers and optional scheduled jobs.
    """
    app = Application.builder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler(["start", "help"], cmd_help))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("summary", cmd_summary))

    # Catch-all message handler (natural language)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Scheduled jobs (only if TELEGRAM_CHAT_ID is set)
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if chat_id and app.job_queue:
        # Deadline check every 2 hours during daytime
        app.job_queue.run_repeating(
            scheduled_deadline_check,
            interval=7200,      # 2 hours
            first=10,           # 10 seconds after startup
            name="deadline_check",
        )

        # Daily digest at 8:00 AM
        app.job_queue.run_daily(
            scheduled_daily_digest,
            time=dt_time(hour=8, minute=0),
            name="daily_digest",
        )

        logger.info("Scheduled jobs registered (chat_id=%s)", chat_id)

    return app


def main() -> None:
    """Entry point: initialize DB, build app, start polling."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        print(
            "Error: TELEGRAM_BOT_TOKEN environment variable is required.\n"
            "Get one from @BotFather on Telegram.\n\n"
            "  export TELEGRAM_BOT_TOKEN='your-token-here'\n"
            "  python bot.py"
        )
        sys.exit(1)

    # Initialize database
    init_db()
    logger.info("Database initialized at %s", init_db.__module__)

    # Build and run
    app = create_app(token)
    logger.info("AI Task Bot starting... (Ctrl+C to stop)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
