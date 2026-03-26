#!/usr/bin/env python3
"""
ADR auto create — git logextractADR draft create.

Usage:
  python3 T9OS/pipes/adr_auto.py                     # 10commit
  python3 T9OS/pipes/adr_auto.py --since 2026-03-19   # date
  python3 T9OS/pipes/adr_auto.py --commit abc123       # commit
  python3 T9OS/pipes/adr_auto.py --dry-run             # createpreview

pipeline : CLAUDE.md 10, L1, memory update .
"""

import argparse
import glob
import os
import re
import subprocess
import sys
from datetime import datetime
from difflib import SequenceMatcher

# project auto
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
DECISIONS_DIR = os.path.join(PROJECT_ROOT, 'T9OS', 'decisions')
INDEX_FILE = os.path.join(DECISIONS_DIR, 'INDEX.md')

# feat:, fix: conventional commit
DECISION_PREFIXES = ('feat:', 'fix:', 'refactor:', 'perf:', 'breaking:')


def get_commits(since=None, commit=None, count=10):
    """git logcommit list."""
    cmd = ['git', '-C', PROJECT_ROOT, 'log', '--format=%H|%s|%ai']

    if commit:
        cmd.append(f'{commit}^..{commit}')
    elif since:
        cmd.extend([f'--since={since}', f'-n{max(count, 50)}'])
    else:
        cmd.append(f'-n{count}')

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print(f"[adr_auto] git log failed: {result.stderr.strip()}", file=sys.stderr)
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("[adr_auto] git execution failed", file=sys.stderr)
        return []

    commits = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('|', 2)
        if len(parts) >= 3:
            commits.append({
                'hash': parts[0],
                'message': parts[1],
                'date': parts[2][:10],  # YYYY-MM-DD
            })
    return commits


def filter_decision_commits(commits):
    """commitfilter."""
    # ADR commit()
    ADR_SKIP_KEYWORDS = ('adr', 'ADR', '', '', '', 'index.md')
    decisions = []
    for c in commits:
        msg_lower = c['message'].lower()
        if any(msg_lower.startswith(p) for p in DECISION_PREFIXES):
            if not any(kw.lower() in msg_lower for kw in ADR_SKIP_KEYWORDS):
                decisions.append(c)
    return decisions


def get_existing_adrs():
    """existing ADR filetitle."""
    adrs = []
    for f in sorted(glob.glob(os.path.join(DECISIONS_DIR, '[0-9][0-9][0-9]-*.md'))):
        basename = os.path.basename(f)
        num_match = re.match(r'^(\d+)-', basename)
        num = int(num_match.group(1)) if num_match else 0

        try:
            with open(f, 'r', encoding='utf-8') as fh:
                first_line = fh.readline().strip()
                title = first_line.lstrip('# ').strip()
        except Exception:
            title = basename

        adrs.append({'num': num, 'title': title, 'filename': basename})
    return adrs


def get_next_adr_number(existing_adrs):
    """next ADR ."""
    if not existing_adrs:
        return 1
    return max(a['num'] for a in existing_adrs) + 1


def is_duplicate(commit_msg, existing_adrs, threshold=0.55):
    """existing ADRtitle duplicate ."""
    # remove
    clean_msg = re.sub(r'^(feat|fix|refactor|perf|breaking):\s*', '', commit_msg).strip()

    for adr in existing_adrs:
        # ADR title"ADR-NNN: " remove
        clean_title = re.sub(r'^ADR-\d+:\s*', '', adr['title']).strip()
        ratio = SequenceMatcher(None, clean_msg.lower(), clean_title.lower()).ratio()
        if ratio >= threshold:
            return True, adr['title'], ratio
    return False, '', 0.0


def slugify(text):
    """commit messagefileconvert."""
    # remove
    clean = re.sub(r'^(feat|fix|refactor|perf|breaking):\s*', '', text).strip()
    # , , /→
    slug = re.sub(r'[^\w-]+', '-', clean.lower()).strip('-')
    #
    if len(slug) > 50:
        slug = slug[:50].rstrip('-')
    return slug


def generate_adr(commit, adr_num):
    """commitADR draftcreate."""
    # type
    msg = commit['message']
    if msg.lower().startswith('feat:'):
        decision_type = '  '
    elif msg.lower().startswith('fix:'):
        decision_type = ' modify'
    elif msg.lower().startswith('refactor:'):
        decision_type = 'refactored'
    elif msg.lower().startswith('perf:'):
        decision_type = ' '
    elif msg.lower().startswith('breaking:'):
        decision_type = 'compatibility change'
    else:
        decision_type = ' '

    # removetitle
    clean_title = re.sub(r'^(feat|fix|refactor|perf|breaking):\s*', '', msg).strip()
    slug = slugify(msg)
    filename = f'{adr_num:03d}-{slug}.md'

    # commit detail (change file list)
    try:
        diff_result = subprocess.run(
            ['git', '-C', PROJECT_ROOT, 'diff-tree', '--no-commit-id', '-r', '--name-only', commit['hash']],
            capture_output=True, text=True, timeout=10
        )
        changed_files = diff_result.stdout.strip().split('\n') if diff_result.stdout.strip() else []
    except Exception:
        changed_files = []

    files_str = ', '.join(f'`{f}`' for f in changed_files[:5])
    if len(changed_files) > 5:
        files_str += f'  {len(changed_files) - 5}'

    content = f"""# ADR-{adr_num:03d}: {clean_title}

- date: {commit['date']}
- state: - commit: `{commit['hash'][:8]}`
- : {clean_title} ({decision_type})
- :
  - (auto create— ccdetail )
  - change file: {files_str if files_str else '(check )'}
- :
  - (auto create— cc)
- result:
  - commit `{commit['hash'][:8]}`implement.

## Simondon Mapping
<!-- TODO: ccmapping-->
implement: (TODO — cc)
"""
    return filename, content


def update_index(new_adrs):
    """INDEX.mdADR itemadd."""
    if not os.path.exists(INDEX_FILE):
        print(f"[adr_auto] INDEX.md not found: {INDEX_FILE}", file=sys.stderr)
        return

    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Superseded item
    superseded_marker = '## Superseded'
    if superseded_marker not in content:
        # Superseded file add
        for adr_num, filename, title, date in new_adrs:
            line = f'| {adr_num:03d} | [{filename}]({filename}) | {title} | {date} |\n'
            content += line
    else:
        insert_lines = ''
        for adr_num, filename, title, date in new_adrs:
            insert_lines += f'| {adr_num:03d} | [{filename}]({filename}) | {title} | {date} |\n'
        content = content.replace(superseded_marker, insert_lines + '\n' + superseded_marker)

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(description='ADR auto create — git log ')
    parser.add_argument('--since', help=' date  commit extract (YYYY-MM-DD)')
    parser.add_argument('--commit', help=' commit hash')
    parser.add_argument('--count', type=int, default=10, help=' N commit (default: 10)')
    parser.add_argument('--dry-run', action='store_true', help='create  preview')
    args = parser.parse_args()

    # decisions check
    if not os.path.isdir(DECISIONS_DIR):
        print(f"[adr_auto] decisions not found: {DECISIONS_DIR}", file=sys.stderr)
        sys.exit(1)

    # 1. commit
    commits = get_commits(since=args.since, commit=args.commit, count=args.count)
    if not commits:
        print("[adr_auto] processcommit not found")
        return

    # 2. commit filter
    decision_commits = filter_decision_commits(commits)
    if not decision_commits:
        print(f"[adr_auto] {len(commits)}commit not found (feat:/fix:/refactor:/perf:/breaking: )")
        return

    # 3. existing ADR
    existing_adrs = get_existing_adrs()
    next_num = get_next_adr_number(existing_adrs)

    # 4. duplicate check + create
    created = []
    skipped = []

    for c in decision_commits:
        is_dup, dup_title, ratio = is_duplicate(c['message'], existing_adrs)
        if is_dup:
            skipped.append((c['message'], dup_title, ratio))
            continue

        filename, content = generate_adr(c, next_num)
        filepath = os.path.join(DECISIONS_DIR, filename)

        # removetitle
        clean_title = re.sub(r'^(feat|fix|refactor|perf|breaking):\s*', '', c['message']).strip()

        if args.dry_run:
            print(f"[dry-run] ADR-{next_num:03d}: {clean_title}")
            print(f"          file: {filename}")
            print(f"          commit: {c['hash'][:8]} ({c['date']})")
            print()
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            created.append((next_num, filename, clean_title, c['date']))
            print(f"[adr_auto] Created: {filename}")

        # createADRduplicate targetadd
        existing_adrs.append({'num': next_num, 'title': f'ADR-{next_num:03d}: {clean_title}', 'filename': filename})
        next_num += 1

    # 5. INDEX.md update
    if created and not args.dry_run:
        update_index(created)
        print(f"[adr_auto] INDEX.md update completed ({len(created)}items add)")

    # 6. result summary
    print(f"\n[adr_auto] summary: commit {len(commits)}, {len(decision_commits)}, "
          f"create {len(created)}, duplicate  {len(skipped)}")

    if skipped:
        print("\n[adr_auto] duplicate:")
        for msg, dup_title, ratio in skipped:
            print(f"  - \"{msg}\" ≈ \"{dup_title}\" (: {ratio:.0%})")

    if created:
        print("\n[adr_auto] TODO: createADRSimondon Mappingcc")


if __name__ == '__main__':
    main()
