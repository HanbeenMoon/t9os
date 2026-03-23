#!/usr/bin/env python3
"""
세션 복구 파이프라인 — 미변환 JSONL → 브리프 일괄 생성
session-end 훅이 안 탄 세션들 전부 복구.

Usage:
  python3 T9OS/pipes/session_recover.py              # 미변환 전부 처리
  python3 T9OS/pipes/session_recover.py --dry-run     # 목록만 출력
  python3 T9OS/pipes/session_recover.py --single ID   # 특정 세션만
"""

import json
import os
import sys
import glob
from pathlib import Path
from datetime import datetime

# 경로
HOME = Path.home()
PROJECT_DIR = Path(os.environ.get("T9OS_WORKSPACE", str(HOME / "workspace")))
JSONL_DIR = HOME / ".claude/projects" / PROJECT_DIR.as_posix().replace("/", "-").lstrip("-")
CONV_DIR = PROJECT_DIR / "T9OS/data/conversations"
BRIEF_DIR = PROJECT_DIR / ".claude/session-briefs"

CONV_DIR.mkdir(parents=True, exist_ok=True)
BRIEF_DIR.mkdir(parents=True, exist_ok=True)

# 교정/결정 감지 키워드
CORRECTION_KW = ['아니', '아닌데', '틀려', '그게아니라', '왜 안', '하지마', '금지', '절대', '접는', '안해', '안 해', '그거아니고', '아니야', '하지 마']
DECISION_KW = ['ㅇㅋ', '좋아', '그렇게', '하자', '해줘', '오케이', 'ㅇㅇ', '접는', '고고', '진행', '승인', '해', 'ㄱㄱ']


def get_converted_ids():
    """이미 변환된 세션 ID 집합"""
    ids = set()
    for md in CONV_DIR.glob("*.md"):
        # 파일명: 20260321_abcd1234.md
        parts = md.stem.split("_", 1)
        if len(parts) == 2:
            ids.add(parts[1])
    return ids


def find_unconverted(min_size=10000):
    """미변환 JSONL 찾기"""
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
    """JSONL에서 대화 MD + 브리프 생성"""
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
                    # MD에는 최대 2000자까지
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
            except:
                pass

    # 브리프 생성
    with open(brief_file, 'w', encoding='utf-8') as brief:
        brief.write(f"# Session Brief — {timestamp} (auto-recovered)\n\n")
        brief.write(f"## 설계자 발언 {len(user_msgs)}개\n\n")

        brief.write(f"## 교정/피드백 {len(corrections)}건\n")
        for c in corrections[-10:]:
            brief.write(f"- {c}\n")

        brief.write(f"\n## 주요 결정 {len(decisions)}건\n")
        for d in decisions[-10:]:
            brief.write(f"- {d}\n")

        # 톤 분석
        brief.write(f"\n## 세션 톤\n")
        angry = sum(1 for m in user_msgs for w in ['시발', '씹', '병신', '지랄', '아오', 'ㅅㅂ'] if w in m)
        positive = sum(1 for m in user_msgs for w in ['좋아', '대박', '오', 'ㅋㅋ', '완벽', '굿'] if w in m)
        if angry > positive:
            brief.write("- 톤: 직설적/불만\n")
        elif positive > angry:
            brief.write("- 톤: 긍정적/만족\n")
        else:
            brief.write("- 톤: 중립적/업무적\n")
        brief.write(f"- 욕설: {angry}회, 긍정: {positive}회\n")

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

    print(f"[세션 복구] 미변환 JSONL: {len(unconverted)}개")

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
            print(f"  [OK] {u['id']} — 설계자 {result['user_msgs']}발언, 교정 {result['corrections']}, 결정 {result['decisions']}")
        except Exception as e:
            fail += 1
            print(f"  [FAIL] {u['id']} — {e}")

    print(f"\n[결과] 성공 {ok}, 실패 {fail}")
    print(f"[총계] 설계자 발언 {total_user}개, 교정 {total_corrections}건, 결정 {total_decisions}건 복구")


if __name__ == '__main__':
    main()
