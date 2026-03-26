#!/usr/bin/env python3
"""AI Session Manager — Read and search Claude Code JSONL sessions in real time.

Works independently of T9OS. Reads Claude Code's native JSONL conversation
files, extracts user/assistant messages, and provides search + sync capabilities.

Usage:
    python3 skill.py                        # List recent sessions
    python3 skill.py --session 636a72df     # Read specific session (first 8 chars of ID)
    python3 skill.py --search "keyword"     # Search across sessions
    python3 skill.py --recent 5             # Show last N sessions
    python3 skill.py --sync                 # Export sessions as Markdown
    python3 skill.py --full --session ID    # Full conversation dump

Environment Variables (optional):
    SESSION_JSONL_DIR   Directory containing .jsonl files
                        Default: ~/.claude/projects/<cwd-slug>/
    SESSION_EXPORT_DIR  Directory for Markdown exports
                        Default: ./session-exports/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _default_jsonl_dir() -> Path:
    """Derive the default JSONL directory from CWD, matching Claude Code's slug format."""
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        return claude_dir  # Will fail gracefully later

    # Claude Code slugs CWD as: replace / with - , strip leading -
    cwd = os.getcwd()
    slug = cwd.replace("/", "-").replace("\\", "-").lstrip("-")

    candidate = claude_dir / slug
    if candidate.exists():
        return candidate

    # Fallback: find most recent project dir
    dirs = sorted(claude_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True)
    for d in dirs:
        if d.is_dir() and list(d.glob("*.jsonl")):
            return d

    return claude_dir


JSONL_DIR = Path(os.environ.get("SESSION_JSONL_DIR", "")) or _default_jsonl_dir()
EXPORT_DIR = Path(os.environ.get("SESSION_EXPORT_DIR", "./session-exports"))


# ---------------------------------------------------------------------------
# Core parsing
# ---------------------------------------------------------------------------

def parse_jsonl(filepath: Path) -> list[dict[str, Any]]:
    """Extract user/assistant messages from a Claude Code JSONL file."""
    msgs: list[dict[str, Any]] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = d.get("type")
            if msg_type not in ("user", "assistant"):
                continue

            role = msg_type
            # Skip internal tool-result messages (non-external user entries)
            if role == "user" and d.get("userType") != "external":
                continue

            content = d.get("message", {}).get("content", "")
            if isinstance(content, list):
                text = " ".join(
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                )
            elif isinstance(content, str):
                text = content
            else:
                text = ""

            ts = d.get("timestamp", "")
            if text.strip():
                msgs.append({"role": role, "text": text.strip(), "ts": ts})

    return msgs


# ---------------------------------------------------------------------------
# Session discovery
# ---------------------------------------------------------------------------

def get_sessions(recent: int | None = None) -> list[dict[str, Any]]:
    """Return JSONL session files sorted by modification time (newest first)."""
    if not JSONL_DIR.exists():
        print(f"JSONL directory not found: {JSONL_DIR}", file=sys.stderr)
        return []

    files = sorted(JSONL_DIR.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if recent:
        files = files[:recent]

    sessions = []
    for f in files:
        stat = f.stat()
        sessions.append({
            "path": f,
            "sid": f.stem[:8],
            "full_id": f.stem,
            "mtime": datetime.fromtimestamp(stat.st_mtime),
            "size_kb": stat.st_size // 1024,
        })
    return sessions


def summarize_session(session: dict[str, Any]) -> dict[str, Any]:
    """Build a summary of a session: message counts and first/last user utterance."""
    msgs = parse_jsonl(session["path"])
    user_msgs = [m for m in msgs if m["role"] == "user"]
    return {
        **session,
        "user_count": len(user_msgs),
        "total_count": len(msgs),
        "first_msg": user_msgs[0]["text"][:100] if user_msgs else "",
        "last_msg": user_msgs[-1]["text"][:100] if user_msgs else "",
    }


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_sessions(keyword: str, recent: int = 50) -> list[dict[str, Any]]:
    """Search JSONL sessions by keyword (case-insensitive)."""
    sessions = get_sessions(recent=recent)
    results = []
    kw_lower = keyword.lower()
    for s in sessions:
        msgs = parse_jsonl(s["path"])
        matches = [m for m in msgs if kw_lower in m["text"].lower()]
        if matches:
            results.append({
                **s,
                "match_count": len(matches),
                "sample": matches[0]["text"][:200],
            })
    return results


# ---------------------------------------------------------------------------
# Markdown export (sync)
# ---------------------------------------------------------------------------

def sync_to_markdown() -> int:
    """Export JSONL sessions as Markdown files. Returns count of newly exported files."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    sessions = get_sessions()
    synced = 0

    for s in sessions:
        existing = list(EXPORT_DIR.glob(f"*_{s['sid']}.md"))
        if existing and existing[0].stat().st_size > 500:
            continue  # Already exported

        msgs = parse_jsonl(s["path"])
        if not msgs:
            continue

        date_str = s["mtime"].strftime("%Y%m%d")
        md_path = EXPORT_DIR / f"{date_str}_{s['sid']}.md"

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Session {s['sid']}\n")
            f.write(f"# Date: {s['mtime'].strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for m in msgs:
                tag = "User" if m["role"] == "user" else "Assistant"
                f.write(f"## [{tag}]\n{m['text'][:2000]}\n\n")

        synced += 1

    return synced


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Session Manager -- read and search Claude Code JSONL sessions"
    )
    parser.add_argument("--session", "-s", help="Session ID prefix (first 8 chars)")
    parser.add_argument("--search", help="Keyword search across sessions")
    parser.add_argument("--recent", "-n", type=int, default=10, help="Number of recent sessions (default 10)")
    parser.add_argument("--sync", action="store_true", help="Export sessions as Markdown")
    parser.add_argument("--full", action="store_true", help="Print full conversation (with --session)")
    args = parser.parse_args()

    if args.sync:
        count = sync_to_markdown()
        print(f"[sync] {count} session(s) exported to {EXPORT_DIR}")
        return

    if args.search:
        results = search_sessions(args.search, recent=args.recent)
        print(f"Search '{args.search}': {len(results)} session(s) matched")
        for r in results:
            print(f"  {r['sid']}  {r['mtime'].strftime('%m/%d %H:%M')}  matches={r['match_count']}")
            print(f"    {r['sample'][:150]}")
        return

    if args.session:
        if not JSONL_DIR.exists():
            print(f"JSONL directory not found: {JSONL_DIR}", file=sys.stderr)
            return
        matches = list(JSONL_DIR.glob(f"{args.session}*.jsonl"))
        if not matches:
            print(f"Session {args.session} not found")
            return
        msgs = parse_jsonl(matches[0])
        user_msgs = [m for m in msgs if m["role"] == "user"]
        print(f"Session {args.session}: {len(user_msgs)} user messages, {len(msgs)} total")
        if args.full:
            for m in msgs:
                tag = "User" if m["role"] == "user" else "Assistant"
                print(f"\n[{tag}] {m['text'][:500]}")
        else:
            print("\nUser messages:")
            for i, m in enumerate(user_msgs):
                print(f"  [{i}] {m['text'][:150]}")
        return

    # Default: list recent sessions
    sessions = get_sessions(recent=args.recent)
    if not sessions:
        print("No sessions found.")
        print(f"Searched: {JSONL_DIR}")
        return

    print(f"Recent {len(sessions)} session(s):")
    for s in sessions:
        summary = summarize_session(s)
        print(
            f"  {s['sid']}  {s['mtime'].strftime('%m/%d %H:%M')}  {s['size_kb']}KB  "
            f"user_msgs={summary['user_count']}"
        )
        if summary["first_msg"]:
            print(f"    first: {summary['first_msg'][:100]}")


if __name__ == "__main__":
    main()
