# ADR-034: Telegram Bot Python Rewrite

- Date: 2026-03-16
- Status: Accepted
- Supersedes: ADR-028
- Decision: Rewrite the Telegram bot from PowerShell to Python, integrating with the T9 Seed engine directly.
- Rationale: PowerShell bot had persistent encoding issues and lacked integration with the Python ecosystem. Python bot can call seed engine functions natively.
- Outcome: `pipes/t9_bot.py` with voice transcription and silent capture

## Simondon Mapping
Concretization — tighter integration between the bot and the seed engine reduces functional abstraction.
