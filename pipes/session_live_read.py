#!/usr/bin/env python3
"""
세션 JSONL 실시간 읽기 — 세션 종료 안 해도 다른 세션이 접근 가능.

Usage:
  python3 T9OS/pipes/session_live_read.py                    # 모든 세션 요약
  python3 T9OS/pipes/session_live_read.py --session 636a72df  # 특정 세션
  python3 T9OS/pipes/session_live_read.py --search "AT1"      # 키워드 검색
  python3 T9OS/pipes/session_live_read.py --recent 5          # 최근 N개 세션
  python3 T9OS/pipes/session_live_read.py --sync              # 전체 conversations/ 동기화
"""

import json, os, sys, glob, argparse
from pathlib import Path
from datetime import datetime

JSONL_DIR = Path.home() / ".claude/projects/-mnt-c-Users-winn-HANBEEN"
CONV_DIR = Path("/mnt/c/Users/winn/HANBEEN/T9OS/data/conversations")
CONV_DIR.mkdir(parents=True, exist_ok=True)


def parse_jsonl(filepath):
    """JSONL 파일에서 user/assistant 메시지 추출."""
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
                    continue  # tool results 등 skip

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
    """모든 세션 JSONL 목록 반환."""
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
    """세션 요약 (user 발언 수, 첫/마지막 발언)."""
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
    """키워드로 세션 검색 — JSONL 직접 검색."""
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
    """전체 JSONL → conversations/ MD 동기화 (세션 종료 안 해도)."""
    sessions = get_sessions()
    synced = 0
    for s in sessions:
        # 기존 MD가 있으면 크기 비교 — JSONL이 더 크면 재생성
        existing = list(CONV_DIR.glob(f"*_{s['sid']}.md"))
        if existing:
            md_size = existing[0].stat().st_size
            jsonl_size = s["path"].stat().st_size
            # JSONL 대비 MD가 충분히 크면 skip (이미 변환됨)
            if md_size > 500:  # 최소 크기 이상이면 이미 있다고 판단
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
    parser = argparse.ArgumentParser(description="세션 JSONL 실시간 읽기")
    parser.add_argument("--session", "-s", help="특정 세션 ID (앞 8자리)")
    parser.add_argument("--search", help="키워드 검색")
    parser.add_argument("--recent", "-n", type=int, default=10, help="최근 N개 세션")
    parser.add_argument("--sync", action="store_true", help="conversations/ 전체 동기화")
    parser.add_argument("--full", action="store_true", help="전체 대화 출력 (--session과 함께)")
    args = parser.parse_args()

    if args.sync:
        count = sync_to_conversations()
        print(f"[live-sync] {count}개 세션 동기화 완료")
        return

    if args.search:
        results = search_sessions(args.search, recent=args.recent)
        print(f"'{args.search}' 검색 결과: {len(results)}개 세션")
        for r in results:
            print(f"  {r['sid']}  {r['mtime'].strftime('%m/%d %H:%M')}  매칭={r['match_count']}건")
            print(f"    {r['sample'][:150]}")
        return

    if args.session:
        # 특정 세션
        matches = list(JSONL_DIR.glob(f"{args.session}*.jsonl"))
        if not matches:
            print(f"세션 {args.session} 없음")
            return
        msgs = parse_jsonl(matches[0])
        user_msgs = [m for m in msgs if m["role"] == "user"]
        print(f"세션 {args.session}: {len(user_msgs)}개 한빈 발언, {len(msgs)}개 총 메시지")
        if args.full:
            for m in msgs:
                prefix = "한빈" if m["role"] == "user" else "cc"
                print(f"\n[{prefix}] {m['text'][:500]}")
        else:
            print("\n한빈 발언:")
            for i, m in enumerate(user_msgs):
                print(f"  [{i}] {m['text'][:150]}")
        return

    # 기본: 최근 세션 요약
    sessions = get_sessions(recent=args.recent)
    print(f"최근 {len(sessions)}개 세션:")
    for s in sessions:
        summary = summarize_session(s)
        print(f"  {s['sid']}  {s['mtime'].strftime('%m/%d %H:%M')}  {s['size_kb']}KB  "
              f"한빈={summary['user_count']}발언")
        if summary["first_msg"]:
            print(f"    첫: {summary['first_msg'][:100]}")


if __name__ == "__main__":
    main()
