# AI Task Bot

A Telegram bot that manages tasks through natural language — in Korean and English.

> Built with patterns from **T9OS** — a personal AI operating system managing 18 production pipelines.

## Features

- **Natural language input** — "내일까지 보고서 제출" or "add report by Friday"
- **Auto-parsing** — extracts title, due date, and priority from free text
- **SQLite storage** — lightweight, zero-config persistence
- **Deadline alerts** — periodic checks with Telegram notifications
- **Daily digest** — automated summary of open tasks and upcoming deadlines
- **Bilingual** — Korean and English supported out of the box
- **AI upgrade path** — swap regex parser for Claude API with one env variable

## Architecture

```
User message
    │
    ▼
┌──────────┐     ┌──────────┐     ┌──────────┐
│  bot.py   │────▶│ parser.py │────▶│  db.py   │
│ (Telegram │     │ (NLP /    │     │ (SQLite) │
│  handler) │     │  regex)   │     └──────────┘
└──────────┘     └──────────┘
    │
    ▼
┌──────────────┐
│ notifier.py  │  ← cron or built-in scheduler
│ (deadline    │
│  alerts)     │
└──────────────┘
```

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url>
cd ai-task-bot
pip install -r requirements.txt    # or: uv pip install -r requirements.txt

# 2. Set your Telegram bot token (get one from @BotFather)
export TELEGRAM_BOT_TOKEN="your-token-here"

# 3. Optional: enable scheduled notifications
export TELEGRAM_CHAT_ID="your-chat-id"

# 4. Optional: enable AI-powered parsing
export ANTHROPIC_API_KEY="sk-ant-..."

# 5. Run
python bot.py
```

## Usage Examples

| You type | Bot understands |
|----------|----------------|
| `내일까지 보고서 제출` | Add task "보고서 제출", due tomorrow |
| `add report by Friday` | Add task "report", due Friday |
| `긴급 서버 점검` | Add task "서버 점검", priority urgent |
| `완료 #3` | Mark task #3 as done |
| `목록` | Show all open tasks |
| `요약` | Daily summary |

## Cron Integration

```crontab
# Deadline alerts every 2 hours (9am-9pm)
0 9-21/2 * * * cd /path/to/ai-task-bot && python notifier.py --check

# Daily digest at 8am
0 8 * * * cd /path/to/ai-task-bot && python notifier.py --digest
```

## File Structure

```
ai-task-bot/
├── bot.py           # Main bot — Telegram handlers + scheduling
├── db.py            # SQLite task database (WAL mode, typed models)
├── parser.py        # Intent parser (regex default, Claude API optional)
├── notifier.py      # Deadline alerts + daily digest
├── requirements.txt # Dependencies
└── README.md        # You are here
```

## Design Decisions

- **Regex-first parsing**: Works offline with zero API cost. The AI backend is an optional upgrade, not a requirement.
- **SQLite with WAL**: Single-file database with concurrent read support. No server needed.
- **Immutable Task dataclass**: All DB results are frozen dataclasses — no accidental mutation.
- **Graceful degradation**: Missing API keys, network errors, or parse failures all have explicit fallback paths.
- **Type hints throughout**: Full Python 3.12+ type annotations for IDE support and static analysis.

## Tech Stack

- Python 3.12+
- python-telegram-bot 21.x
- SQLite 3 (stdlib)
- Claude API (optional, for AI-powered intent parsing)

## License

MIT
