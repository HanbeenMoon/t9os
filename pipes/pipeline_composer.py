#!/usr/bin/env python3
"""T9 OS v2 — Pipeline Composer v0.1
Preindividual(preindividual) auto classify + .
247auto engine.

role (t9_auto.py):
- pipeline_composer: () + urgency config
- t9_auto.py: concepts extract + project classify (Gemini )
- execution : composer → autoconcepts
classify rule (deterministic, ):
1. deadline key→ deadline_notify + urgency config
2. schedule/calendar key→ calendar_sync
3. /key→ session 4. /key→ conversation 5. key→ t9-research
6. → record (capture)

Usage:
    python3 T9OS/pipes/pipeline_composer.py              # total preindividual classify
    python3 T9OS/pipes/pipeline_composer.py --dry-run     # preview (execution )
    python3 T9OS/pipes/pipeline_composer.py --limit 10
"""

import sqlite3
import os
import sys
import re
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.config import DB_PATH

# classify rule (pattern → )
RULES = [
    {
        'name': 'deadline',
        'patterns': [
            r'deadline|deadline|~|D-\d|||due|until|||',
            r'\d{1,2}/\d{1,2}|\d{1,2}\s*\d{1,2}',
        ],
        'action': 'deadline_notify',
        'urgency': 'high',
    },
    {
        'name': 'calendar',
        'patterns': [r'schedule|calendar||||||zoom||'],
        'action': 'calendar_sync',
        'urgency': 'mid',
    },
    {
        'name': 'code',
        'patterns': [r'|||deploy|deploy|git|API|function|script|pipeline|implement|'],
        'action': 'code_session',
        'urgency': 'mid',
    },
    {
        'name': 'research',
        'patterns': [r'||||analyze||statistics|search||'],
        'action': 't9_research',
        'urgency': 'mid',
    },
    {
        'name': 'emotion',
        'patterns': [r'(?<!\w)(|[]|\s*|[]||||[]|[]|[])'],
        'action': 'dialogue',
        'urgency': 'low',
    },
    {
        'name': 'idea',
        'patterns': [r'||||||||'],
        'action': 'archive',
        'urgency': 'low',
    },
]

def classify(text: str) -> dict:
    """rule classify."""
    text_lower = text.lower()
    matches = []

    for rule in RULES:
        for pattern in rule['patterns']:
            if re.search(pattern, text_lower):
                matches.append(rule)
                break

    if not matches:
        return {'name': 'archive', 'action': 'archive', 'urgency': 'low'}

    # priority: deadline > calendar > code > research > emotion > idea
    priority = ['deadline', 'calendar', 'code', 'research', 'emotion', 'idea']
    matches.sort(key=lambda m: priority.index(m['name']) if m['name'] in priority else 99)

    return matches[0]

def process_preindividuals(dry_run=False, limit=None):
    """preindividual classify."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    query = "SELECT id, filename, body_preview, metadata, urgency FROM entities WHERE phase = 'preindividual'"
    if limit:
        query += f" LIMIT {limit}"

    rows = c.execute(query).fetchall()
    results = {'deadline': 0, 'calendar': 0, 'code': 0, 'research': 0,
               'emotion': 0, 'idea': 0, 'archive': 0}

    for row in rows:
        text = f"{row['filename'] or ''} {row['body_preview'] or ''}"
        meta = json.loads(row['metadata']) if row['metadata'] else {}

        classification = classify(text)
        results[classification['name']] = results.get(classification['name'], 0) + 1

        if dry_run:
            print(f"  [{classification['name']:10}] {row['filename'][:60]}")
            continue

        # urgency
        if classification['urgency'] == 'high' and row['urgency'] != 'high':
            c.execute("UPDATE entities SET urgency = 'high' WHERE id = ?", (row['id'],))

        # metadataclassify result save
        meta['auto_classified'] = classification['name']
        meta['auto_action'] = classification['action']
        meta['classified_at'] = datetime.now().isoformat()
        c.execute("UPDATE entities SET metadata = ? WHERE id = ?",
                  (json.dumps(meta, ensure_ascii=False), row['id']))

        # tension_detected(classify= Tension )
        if classification['name'] in ('deadline', 'code', 'research'):
            c.execute("UPDATE entities SET phase = 'tension_detected' WHERE id = ? AND phase = 'preindividual'",
                      (row['id'],))
            c.execute("INSERT INTO transitions (entity_id, from_phase, to_phase, timestamp, reason) VALUES (?, 'preindividual', 'tension_detected', ?, ?)",
                      (row['id'], datetime.now().isoformat(), f"Pipeline Composer: {classification['name']}"))

    if not dry_run:
        conn.commit()
    conn.close()

    # result output
    total = sum(results.values())
    print(f"\n{'='*50}")
    print(f"Pipeline Composer v0.1 — {'DRY RUN' if dry_run else 'EXECUTED'}")
    print(f"{'='*50}")
    print(f"Total processed: {total}")
    for cat, cnt in sorted(results.items(), key=lambda x: -x[1]):
        if cnt > 0:
            bar = '█' * min(cnt, 40)
            print(f"  {cat:12} {cnt:4} {bar}")

    return results

if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    limit = None
    for i, arg in enumerate(sys.argv):
        if arg == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])

    process_preindividuals(dry_run=dry_run, limit=limit)
