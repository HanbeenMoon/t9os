# Auto Pipeline Router

A rule-based text classification and routing engine. Takes unstructured text (notes, tasks, messages, ideas) and classifies them into actionable categories using deterministic regex rules.

## What it does

1. **Classify** a single text string into a category (deadline, calendar, code, research, etc.)
2. **Route** items from a SQLite database or JSON file, writing classifications back
3. **Custom rules** via JSON -- bring your own classification logic

Classification is deterministic (regex, no LLM calls), fast, and reproducible.

## Built-in categories

| Priority | Category | Urgency | Description |
|----------|----------|---------|-------------|
| 1 | deadline | high | Items with due dates or time pressure |
| 2 | calendar | mid | Meetings, appointments, scheduled events |
| 3 | code | mid | Development tasks, bugs, deployments |
| 4 | research | mid | Investigation and analysis tasks |
| 5 | communication | mid | Emails, follow-ups, messages |
| 6 | idea | low | Brainstorming and inspiration |
| -- | uncategorized | low | Fallback for unmatched items |

## Requirements

- Python 3.10+
- No external dependencies (stdlib only)

## Installation

```bash
# Just copy skill.py
cp skill.py /your/project/pipeline_router.py
```

## Usage

### Classify a single text

```bash
python3 skill.py classify "Meeting with design team tomorrow at 2pm"
# Category:  calendar
# Action:    calendar_sync
# Urgency:   mid

python3 skill.py classify "Bug in auth module, needs fix before Friday" --json
# {"name": "code", "action": "code_session", "urgency": "mid"}
```

### Route items from SQLite

```bash
# Classify all rows where status is 'pending'
python3 skill.py route --db tasks.db --table tasks --text-col description --where "status='pending'"

# Dry run (preview only)
python3 skill.py route --db tasks.db --table tasks --text-col description --dry-run

# Limit to 50 items
python3 skill.py route --db tasks.db --table tasks --text-col description --limit 50
```

The tool automatically adds `classification`, `action`, `urgency`, and `classified_at` columns to your table.

### Route items from JSON

```bash
# Input: [{"id": 1, "text": "Deploy API by Friday"}, ...]
python3 skill.py route --input items.json --text-field text --output classified.json
```

### List built-in rules

```bash
python3 skill.py rules
```

## Custom rules

Create a JSON file with your own rules:

```json
[
  {
    "name": "billing",
    "patterns": ["invoice|payment|billing|subscription|charge"],
    "action": "billing_queue",
    "urgency": "high",
    "description": "Billing and payment related items"
  },
  {
    "name": "support",
    "patterns": ["help|support|issue|problem|broken|not working"],
    "action": "support_ticket",
    "urgency": "mid",
    "description": "Customer support requests"
  }
]
```

Use with:

```bash
python3 skill.py classify "Payment failed for subscription" --rules my_rules.json
python3 skill.py route --db items.db --table items --text-col body --rules my_rules.json
```

Rules are evaluated in order -- the first match wins. Place higher-priority rules earlier in the list.

## Python API

```python
from skill import classify, classify_batch, load_rules

# Single classification
result = classify("Deploy the API before Friday deadline")
print(result)  # {"name": "deadline", "action": "deadline_alert", "urgency": "high"}

# Batch classification
items = [
    {"text": "Fix login bug", "id": 1},
    {"text": "Team standup at 10am", "id": 2},
]
classified = classify_batch(items, text_key="text")

# Custom rules
rules = load_rules("my_rules.json")
result = classify("Invoice #1234 overdue", rules=rules)
```

## Integration with Claude Code

Add to your `CLAUDE.md`:

```markdown
## Auto-classify inbox items
Run `python3 /path/to/skill.py route --db data.db --table inbox --text-col body --dry-run` to preview classifications.
```
