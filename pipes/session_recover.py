#!/usr/bin/env python3
"""
session recover pipeline — convert JSONL → brief create
session-end sessionrecover.

Usage:
  python3 T9OS/pipes/session_recover.py              # convert process
  python3 T9OS/pipes/session_recover.py --dry-run     # listoutput
  python3 T9OS/pipes/session_recover.py --single ID   # session
"""

import json
import os
import sys
import glob
from pathlib import Path
from datetime import datetime

# path
HOME = Path.home()
PROJECT_DIR = Path("/mnt/c/Users/winn/HANBEEN")
JSONL_DIR = HOME / ".claude/projects/-mnt-c-Users-winn-HANBEEN"
CONV_DIR = PROJECT_DIR / "T9OS/data/conversations"
BRIEF_DIR = PROJECT_DIR / ".claude/session-briefs"

CONV_DIR.mkdir(parents=True, exist_ok=True)
BRIEF_DIR.mkdir(parents=True, exist_ok=True)

# /key
CORRECTION_KW = ['', '', '', '', ' ', '', '', '', '', '', ' ', '', '', ' ']
DECISION_KW = ['ㅇㅋ', '', '', '', '', '', 'ㅇㅇ', '', '', '', 'approval', '', 'ㄱㄱ']


def get_converted_ids():
    """convertsession ID """
    ids = set()
    for md in CONV_DIR.glob("*.md"):
        # file: 20260321_abcd1234.md
        parts = md.stem.split("_", 1)
        if len(parts) == 2:
            ids.add(parts[1])
    return ids


def find_unconverted(min_size=10000):
    """convert JSONL """
    converted = get_converted_ids()
    unconverted = []

    for jsonl in sorted(JSONL_DIR.glob("*.jsonl")):
        if "subagents" in str(jsonl):
            continue
        size = jsonl.stat().st_size
        if size < min_size:
            continue

        session_id = jsonl.stem[:8]
        if session_id not in converted:
            mtime = datetime.fromtimestamp(jsonl.stat().st_mtime)
            unconverted.append({
                'path': jsonl,
                'id': session_id,
                'full_id': jsonl.stem,
                'size': size,
                'date': mtime,
            })

    return unconverted


def extract_brief(jsonl_path, session_id, date_str=None):
    """JSONLconversation MD + brief create"""
    if date_str is None:
        mtime = datetime.fromtimestamp(jsonl_path.stat().st_mtime)
        date_str = mtime.strftime("%Y%m%d")

    timestamp = datetime.fromtimestamp(jsonl_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

    conv_file = CONV_DIR / f"{date_str}_{session_id}.md"
    brief_file = BRIEF_DIR / f"{date_str}_{session_id}_brief.md"

    lines = open(jsonl_path, 'r', encoding='utf-8', errors='replace').readlines()

    user_msgs = []
    corrections = []
    decisions = []
    assistant_msgs = []

    with open(conv_file, 'w', encoding='utf-8') as conv:
        conv.write(f"# CC Session {session_id} (auto-recovered)\n")
        conv.write(f"# Date: {timestamp}\n\n")

        for line in lines:
            try:
                msg = json.loads(line)
                role = msg.get('role', msg.get('type', ''))
                content = ''

                if isinstance(msg.get('message', {}).get('content', ''), str):
                    content = msg['message']['content']
                elif isinstance(msg.get('message', {}).get('content', []), list):
                    for part in msg['message']['content']:
                        if isinstance(part, dict) and part.get('type') == 'text':
                            content += part.get('text', '') + '\n'
                        elif isinstance(part, str):
                            content += part + '\n'

                if content.strip() and role in ('user', 'assistant', 'human'):
                    # MDmax 2000
                    conv.write(f"## [{role}]\n{content.strip()[:2000]}\n\n")

                    if role in ('user', 'human'):
                        user_msgs.append(content.strip())
                        for kw in CORRECTION_KW:
                            if kw in content:
                                corrections.append(content.strip()[:150])
                                break
                        for kw in DECISION_KW:
                            if kw in content:
                                decisions.append(content.strip()[:150])
                                break
                    elif role == 'assistant':
                        assistant_msgs.append(content.strip()[:200])
            except Exception:
                continue

    # brief create
    with open(brief_file, 'w', encoding='utf-8') as brief:
        brief.write(f"# Session Brief — {timestamp} (auto-recovered)\n\n")
        brief.write(f"## {len(user_msgs)}\n\n")

        brief.write(f"## /{len(corrections)}items\n")
        for c in corrections[-10:]:
            brief.write(f"- {c}\n")

        brief.write(f"\n## {len(decisions)}items\n")
        for d in decisions[-10:]:
            brief.write(f"- {d}\n")

        # analyze
        brief.write(f"\n## session \n")
        angry = sum(1 for m in user_msgs for w in ['', '', '', '', '', 'ㅅㅂ'] if w in m)
        positive = sum(1 for m in user_msgs for w in ['', '', '', 'ㅋㅋ', '', ''] if w in m)
        if angry > positive:
            brief.write("- : /\n")
        elif positive > angry:
            brief.write("- : /\n")
        else:
            brief.write("- : /\n")
        brief.write(f"- : {angry}, : {positive}\n")

    return {
        'conv': str(conv_file),
        'brief': str(brief_file),
        'user_msgs': len(user_msgs),
        'corrections': len(corrections),
        'decisions': len(decisions),
    }


def main():
    dry_run = '--dry-run' in sys.argv
    single = None
    if '--single' in sys.argv:
        idx = sys.argv.index('--single')
        if idx + 1 < len(sys.argv):
            single = sys.argv[idx + 1]

    unconverted = find_unconverted()

    if single:
        unconverted = [u for u in unconverted if u['id'] == single or u['full_id'].startswith(single)]

    print(f"[session recover] convert JSONL: {len(unconverted)}")

    if dry_run:
        for u in unconverted:
            print(f"  {u['id']}  {u['size']:>10,} bytes  {u['date'].strftime('%Y-%m-%d %H:%M')}")
        return

    ok, fail = 0, 0
    total_user = 0
    total_corrections = 0
    total_decisions = 0

    for u in unconverted:
        try:
            date_str = u['date'].strftime("%Y%m%d")
            result = extract_brief(u['path'], u['id'], date_str)
            ok += 1
            total_user += result['user_msgs']
            total_corrections += result['corrections']
            total_decisions += result['decisions']
            print(f"  [OK] {u['id']} — {result['user_msgs']}, {result['corrections']}, {result['decisions']}")
        except Exception as e:
            fail += 1
            print(f"  [FAIL] {u['id']} — {e}")

    print(f"\n[result] success {ok}, failed {fail}")
    print(f"[] {total_user}, {total_corrections}items, {total_decisions}items recover")


if __name__ == '__main__':
    main()
