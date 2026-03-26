# ADR-013: Telegram Bot Silent Inbox Mode

- Date: 2026-03-19
- Status: Accepted
- Decision: Default Telegram bot behavior is silent inbox capture — all messages stored as preindividuals in `field/inbox/`, no bot response. Only explicit commands (/status, /daily) get responses.
- Rationale: Telegram is the fastest input channel while mobile. Minimizing friction is essential. Bot responses create conversational expectations; Telegram is an input channel, not a chat interface.
- Outcome: `pipes/t9_bot.py` with silent capture mode

## Simondon Mapping
Zero Decision UX — capture without classification mirrors the preindividual's resistance to premature form-imposition.
