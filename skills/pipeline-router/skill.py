#!/usr/bin/env python3
"""Auto Pipeline Router — Rule-based text classification and routing engine.

Classifies text items (notes, messages, tasks, ideas) into categories using
deterministic regex rules, then optionally routes them by updating a SQLite
database or writing classification results to JSON.

Works standalone with zero external dependencies. Bring your own rules or
use the built-in defaults.

Usage:
    # Classify a single text
    python3 skill.py classify "Meeting with team tomorrow at 3pm about deployment"

    # Classify items from a SQLite database
    python3 skill.py route --db items.db --table items --text-col body

    # Classify items from a JSON file
    python3 skill.py route --input items.json --text-field body

    # Dry run (no writes)
    python3 skill.py route --db items.db --table items --text-col body --dry-run

    # Use custom rules
    python3 skill.py classify "text" --rules custom_rules.json

    # List built-in rules
    python3 skill.py rules
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Built-in classification rules (ordered by priority, highest first)
# ---------------------------------------------------------------------------

BUILTIN_RULES: list[dict[str, Any]] = [
    {
        "name": "deadline",
        "patterns": [
            r"deadline|due\s+date|due\s+by|submit|submission|expires?|by\s+\w+day",
            r"D-\d+|due\s+(today|tomorrow|this\s+week)",
            r"\d{1,2}/\d{1,2}|\d{4}-\d{2}-\d{2}",
        ],
        "action": "deadline_alert",
        "urgency": "high",
        "description": "Items with explicit deadlines or time pressure",
    },
    {
        "name": "calendar",
        "patterns": [
            r"meeting|appointment|schedule|calendar|at\s+\d{1,2}(:\d{2})?\s*(am|pm)?",
            r"zoom|teams\s+call|standup|sync|1:1|one-on-one",
        ],
        "action": "calendar_sync",
        "urgency": "mid",
        "description": "Calendar events, meetings, and time-specific items",
    },
    {
        "name": "code",
        "patterns": [
            r"bug|error|exception|deploy|git|API|function|script|pipeline|build|PR|pull\s+request",
            r"refactor|test|debug|crash|fix|patch|release|merge",
        ],
        "action": "code_session",
        "urgency": "mid",
        "description": "Code, development, and technical tasks",
    },
    {
        "name": "research",
        "patterns": [
            r"research|investigate|paper|study|analysis|data|survey|review\s+literature",
            r"look\s+into|find\s+out|compare|benchmark|evaluate",
        ],
        "action": "research_queue",
        "urgency": "mid",
        "description": "Research tasks and information gathering",
    },
    {
        "name": "communication",
        "patterns": [
            r"email|reply|respond|follow\s+up|reach\s+out|contact|message|slack|ping",
        ],
        "action": "comm_queue",
        "urgency": "mid",
        "description": "Communication and follow-up tasks",
    },
    {
        "name": "idea",
        "patterns": [
            r"idea|inspiration|what\s+if|maybe\s+we|could\s+try|brainstorm|concept|thought",
        ],
        "action": "archive",
        "urgency": "low",
        "description": "Ideas and brainstorming notes",
    },
]

DEFAULT_FALLBACK = {"name": "uncategorized", "action": "archive", "urgency": "low"}


# ---------------------------------------------------------------------------
# Classification engine
# ---------------------------------------------------------------------------

def load_rules(rules_path: str | None = None) -> list[dict[str, Any]]:
    """Load classification rules from a JSON file or return built-in defaults."""
    if rules_path:
        path = Path(rules_path)
        if not path.exists():
            print(f"Rules file not found: {rules_path}", file=sys.stderr)
            sys.exit(1)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return BUILTIN_RULES


def classify(text: str, rules: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Classify text against rules. Returns the highest-priority matching rule."""
    if rules is None:
        rules = BUILTIN_RULES

    text_lower = text.lower()
    matches: list[dict[str, Any]] = []

    for rule in rules:
        for pattern in rule["patterns"]:
            if re.search(pattern, text_lower):
                matches.append(rule)
                break

    if not matches:
        return dict(DEFAULT_FALLBACK)

    # Rules list is already priority-ordered; return the first match
    return {
        "name": matches[0]["name"],
        "action": matches[0].get("action", "archive"),
        "urgency": matches[0].get("urgency", "low"),
    }


def classify_batch(items: list[dict[str, Any]], text_key: str = "text", rules: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Classify a list of dicts. Adds 'classification' key to each item."""
    results = []
    for item in items:
        text = str(item.get(text_key, ""))
        classification = classify(text, rules)
        results.append({
            **item,
            "classification": classification["name"],
            "action": classification["action"],
            "urgency": classification["urgency"],
            "classified_at": datetime.now().isoformat(),
        })
    return results


# ---------------------------------------------------------------------------
# Database routing
# ---------------------------------------------------------------------------

def route_from_db(
    db_path: str,
    table: str,
    text_col: str,
    rules: list[dict[str, Any]] | None = None,
    id_col: str = "id",
    where: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Classify rows from a SQLite table and optionally update metadata.

    Adds/updates columns: classification, action, urgency, classified_at.
    If columns do not exist, creates them automatically.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Ensure classification columns exist
    if not dry_run:
        for col_name, col_type in [
            ("classification", "TEXT"),
            ("action", "TEXT"),
            ("urgency", "TEXT"),
            ("classified_at", "TEXT"),
        ]:
            try:
                conn.execute(f"ALTER TABLE [{table}] ADD COLUMN [{col_name}] {col_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists

    query = f"SELECT [{id_col}], [{text_col}] FROM [{table}]"
    conditions = []
    if where:
        conditions.append(where)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    if limit:
        query += f" LIMIT {limit}"

    rows = conn.execute(query).fetchall()

    counts: dict[str, int] = {}
    for row in rows:
        text = str(row[text_col] or "")
        result = classify(text, rules)
        cat = result["name"]
        counts[cat] = counts.get(cat, 0) + 1

        if dry_run:
            print(f"  [{cat:15}] {text[:80]}")
            continue

        conn.execute(
            f"UPDATE [{table}] SET classification=?, action=?, urgency=?, classified_at=? WHERE [{id_col}]=?",
            (result["name"], result["action"], result["urgency"], datetime.now().isoformat(), row[id_col]),
        )

    if not dry_run:
        conn.commit()
    conn.close()

    return counts


# ---------------------------------------------------------------------------
# JSON routing
# ---------------------------------------------------------------------------

def route_from_json(
    input_path: str,
    text_field: str = "text",
    rules: list[dict[str, Any]] | None = None,
    output_path: str | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Classify items from a JSON array file."""
    with open(input_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    if not isinstance(items, list):
        print("Input JSON must be an array of objects", file=sys.stderr)
        sys.exit(1)

    classified = classify_batch(items, text_key=text_field, rules=rules)

    counts: dict[str, int] = {}
    for item in classified:
        cat = item["classification"]
        counts[cat] = counts.get(cat, 0) + 1
        if dry_run:
            text = str(item.get(text_field, ""))[:80]
            print(f"  [{cat:15}] {text}")

    if not dry_run and output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(classified, f, ensure_ascii=False, indent=2)

    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_summary(counts: dict[str, int], dry_run: bool) -> None:
    """Print classification summary."""
    total = sum(counts.values())
    mode = "DRY RUN" if dry_run else "EXECUTED"
    print(f"\n{'='*50}")
    print(f"Auto Pipeline Router -- {mode}")
    print(f"{'='*50}")
    print(f"Total processed: {total}")
    for cat, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        if cnt > 0:
            bar = "#" * min(cnt, 40)
            print(f"  {cat:15} {cnt:4}  {bar}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto Pipeline Router -- rule-based text classification and routing"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # classify
    cls_parser = subparsers.add_parser("classify", help="Classify a single text")
    cls_parser.add_argument("text", help="Text to classify")
    cls_parser.add_argument("--rules", help="Custom rules JSON file")
    cls_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # route
    route_parser = subparsers.add_parser("route", help="Classify and route items from DB or JSON")
    route_parser.add_argument("--db", help="SQLite database path")
    route_parser.add_argument("--table", default="items", help="Table name (default: items)")
    route_parser.add_argument("--text-col", default="body", help="Text column (default: body)")
    route_parser.add_argument("--id-col", default="id", help="ID column (default: id)")
    route_parser.add_argument("--where", help="SQL WHERE clause (e.g., \"status='pending'\")")
    route_parser.add_argument("--input", help="Input JSON file (alternative to --db)")
    route_parser.add_argument("--text-field", default="text", help="JSON text field (default: text)")
    route_parser.add_argument("--output", help="Output JSON file (for --input mode)")
    route_parser.add_argument("--rules", help="Custom rules JSON file")
    route_parser.add_argument("--limit", type=int, help="Max items to process")
    route_parser.add_argument("--dry-run", action="store_true", help="Preview without writing")

    # rules
    subparsers.add_parser("rules", help="List built-in classification rules")

    args = parser.parse_args()

    if args.command == "classify":
        rules = load_rules(args.rules) if args.rules else None
        result = classify(args.text, rules)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Category:  {result['name']}")
            print(f"Action:    {result['action']}")
            print(f"Urgency:   {result['urgency']}")

    elif args.command == "route":
        rules = load_rules(args.rules) if args.rules else None

        if args.db:
            counts = route_from_db(
                db_path=args.db,
                table=args.table,
                text_col=args.text_col,
                id_col=args.id_col,
                where=args.where,
                rules=rules,
                limit=args.limit,
                dry_run=args.dry_run,
            )
        elif args.input:
            counts = route_from_json(
                input_path=args.input,
                text_field=args.text_field,
                rules=rules,
                output_path=args.output,
                dry_run=args.dry_run,
            )
        else:
            print("Provide --db or --input", file=sys.stderr)
            sys.exit(1)

        print_summary(counts, args.dry_run)

    elif args.command == "rules":
        print("Built-in classification rules (priority order):\n")
        for i, rule in enumerate(BUILTIN_RULES, 1):
            print(f"  {i}. {rule['name']:15} [{rule.get('urgency', 'low'):4}]  {rule.get('description', '')}")
            for p in rule["patterns"]:
                print(f"     pattern: {p}")
            print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
