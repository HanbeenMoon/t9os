#!/usr/bin/env python3
"""
session JSONL — session end sessionaccess .

Usage:
  python3 T9OS/pipes/session_live_read.py                    # session summary
  python3 T9OS/pipes/session_live_read.py --session 636a72df  # session
  python3 T9OS/pipes/session_live_read.py --search "AT1"      # keysearch
  python3 T9OS/pipes/session_live_read.py --recent 5          # Nsession
  python3 T9OS/pipes/session_live_read.py --sync              # total conversations/ sync
"""

import json, os, sys, glob, argparse
from pathlib import Path
from datetime import datetime

JSONL_DIR = Path.home() / ".claude/projects/-mnt-c-Users-winn-HANBEEN"
CONV_DIR = Path("/mnt/c/Users/winn/HANBEEN/T9OS/data/conversations")
CONV_DIR.mkdir(parents=True, exist_ok=True)


def parse_jsonl(filepath):
    """JSONL fileuser/assistant message extract."""
    msgs = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                msg_type = d.get("type")
                if msg_type not in ("user", "assistant"):
                    continue

                role = msg_type
                is_external = d.get("userType") == "external" if role == "user" else True
                if role == "user" and not is_external:
                    continue  # tool results skip

                content = d.get("message", {}).get("content", "")
                if isinstance(content, list):
                    text = " ".join(
                        c.get("text", "") for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    )
                elif isinstance(content, str):
                    text = content
                else:
                    text = ""

                ts = d.get("timestamp", "")
                if text.strip():
                    msgs.append({"role": role, "text": text.strip(), "ts": ts})
            except (json.JSONDecodeError, KeyError):
                continue
    return msgs


def get_sessions(recent=None):
    """session JSONL list return."""
    files = sorted(JSONL_DIR.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if recent:
        files = files[:recent]
    sessions = []
    for f in files:
        sid = f.stem[:8]
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        size_kb = f.stat().st_size // 1024
        sessions.append({"path": f, "sid": sid, "full_id": f.stem, "mtime": mtime, "size_kb": size_kb})
    return sessions


def summarize_session(session):
    """session summary (user , /)."""
    msgs = parse_jsonl(session["path"])
    user_msgs = [m for m in msgs if m["role"] == "user"]
    return {
        **session,
        "user_count": len(user_msgs),
        "total_count": len(msgs),
        "first_msg": user_msgs[0]["text"][:100] if user_msgs else "",
        "last_msg": user_msgs[-1]["text"][:100] if user_msgs else "",
    }


def search_sessions(keyword, recent=50):
    """keysession search — JSONL search."""
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


def sync_to_conversations():
    """total JSONL → conversations/ MD sync (session end )."""
    sessions = get_sessions()
    synced = 0
    for s in sessions:
        # existing MDsize compare — JSONLcreate
        existing = list(CONV_DIR.glob(f"*_{s['sid']}.md"))
        if existing:
            md_size = existing[0].stat().st_size
            jsonl_size = s["path"].stat().st_size
            # JSONL MDskip (convert)
            if md_size > 500:  # min size
                continue

        msgs = parse_jsonl(s["path"])
        if not msgs:
            continue

        date_str = s["mtime"].strftime("%Y%m%d")
        md_path = CONV_DIR / f"{date_str}_{s['sid']}.md"

        user_msgs = [m for m in msgs if m["role"] == "user"]
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# CC Session {s['sid']} (live-sync)\n")
            f.write(f"# Date: {s['mtime'].strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for m in msgs:
                f.write(f"## [{m['role']}]\n{m['text'][:2000]}\n\n")

        synced += 1

    return synced


def main():
    parser = argparse.ArgumentParser(description="session JSONL  ")
    parser.add_argument("--session", "-s", help=" session ID ( 8)")
    parser.add_argument("--search", help="key search")
    parser.add_argument("--recent", "-n", type=int, default=10, help=" N session")
    parser.add_argument("--sync", action="store_true", help="conversations/ total sync")
    parser.add_argument("--full", action="store_true", help="total conversation output (--session )")
    args = parser.parse_args()

    if args.sync:
        count = sync_to_conversations()
        print(f"[live-sync] {count}session sync completed")
        return

    if args.search:
        results = search_sessions(args.search, recent=args.recent)
        print(f"'{args.search}' search result: {len(results)}session")
        for r in results:
            print(f"  {r['sid']}  {r['mtime'].strftime('%m/%d %H:%M')}  ={r['match_count']}items")
            print(f"    {r['sample'][:150]}")
        return

    if args.session:
        # session
        matches = list(JSONL_DIR.glob(f"{args.session}*.jsonl"))
        if not matches:
            print(f"session {args.session} not found")
            return
        msgs = parse_jsonl(matches[0])
        user_msgs = [m for m in msgs if m["role"] == "user"]
        print(f"session {args.session}: {len(user_msgs)}, {len(msgs)}message")
        if args.full:
            for m in msgs:
                prefix = "" if m["role"] == "user" else "cc"
                print(f"\n[{prefix}] {m['text'][:500]}")
        else:
            print("\n:")
            for i, m in enumerate(user_msgs):
                print(f"  [{i}] {m['text'][:150]}")
        return

    # default: session summary
    sessions = get_sessions(recent=args.recent)
    print(f"{len(sessions)}session:")
    for s in sessions:
        summary = summarize_session(s)
        print(f"  {s['sid']}  {s['mtime'].strftime('%m/%d %H:%M')}  {s['size_kb']}KB  "
              f"={summary['user_count']}")
        if summary["first_msg"]:
            print(f"    : {summary['first_msg'][:100]}")


if __name__ == "__main__":
    main()
