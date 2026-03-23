#!/usr/bin/env python3
"""
ADR 자동 생성 — git log에서 결정 사항을 추출하여 ADR 초안 생성.

사용법:
  python3 T9OS/pipes/adr_auto.py                     # 최근 10개 커밋
  python3 T9OS/pipes/adr_auto.py --since 2026-03-19   # 특정 날짜 이후
  python3 T9OS/pipes/adr_auto.py --commit abc123       # 특정 커밋
  python3 T9OS/pipes/adr_auto.py --dry-run             # 생성하지 않고 미리보기만

파이프라인 레지스트리: CLAUDE.md 섹션 10, L1, memory 동시 갱신 필요.
"""

import argparse
import glob
import os
import re
import subprocess
import sys
from datetime import datetime
from difflib import SequenceMatcher

# 프로젝트 루트 자동 탐지
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
DECISIONS_DIR = os.path.join(PROJECT_ROOT, 'T9OS', 'decisions')
INDEX_FILE = os.path.join(DECISIONS_DIR, 'INDEX.md')

# feat:, fix: 등 conventional commit 접두사
DECISION_PREFIXES = ('feat:', 'fix:', 'refactor:', 'perf:', 'breaking:')


def get_commits(since=None, commit=None, count=10):
    """git log에서 커밋 목록을 가져온다."""
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
            print(f"[adr_auto] git log 실패: {result.stderr.strip()}", file=sys.stderr)
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("[adr_auto] git 실행 실패", file=sys.stderr)
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
    """결정 사항이 될 수 있는 커밋만 필터링한다."""
    # ADR 관련 커밋은 제외 (무한루프 방지)
    ADR_SKIP_KEYWORDS = ('adr', 'ADR', '소급', '마이그레이션', '툴팁', 'index.md')
    decisions = []
    for c in commits:
        msg_lower = c['message'].lower()
        if any(msg_lower.startswith(p) for p in DECISION_PREFIXES):
            if not any(kw.lower() in msg_lower for kw in ADR_SKIP_KEYWORDS):
                decisions.append(c)
    return decisions


def get_existing_adrs():
    """기존 ADR 파일들의 제목과 번호를 수집한다."""
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
    """다음 ADR 번호를 계산한다."""
    if not existing_adrs:
        return 1
    return max(a['num'] for a in existing_adrs) + 1


def is_duplicate(commit_msg, existing_adrs, threshold=0.55):
    """기존 ADR과의 제목 유사도로 중복 여부를 판단한다."""
    # 접두사 제거
    clean_msg = re.sub(r'^(feat|fix|refactor|perf|breaking):\s*', '', commit_msg).strip()

    for adr in existing_adrs:
        # ADR 제목에서 "ADR-NNN: " 접두사 제거
        clean_title = re.sub(r'^ADR-\d+:\s*', '', adr['title']).strip()
        ratio = SequenceMatcher(None, clean_msg.lower(), clean_title.lower()).ratio()
        if ratio >= threshold:
            return True, adr['title'], ratio
    return False, '', 0.0


def slugify(text):
    """커밋 메시지를 파일명용 슬러그로 변환한다."""
    # 접두사 제거
    clean = re.sub(r'^(feat|fix|refactor|perf|breaking):\s*', '', text).strip()
    # 한글 유지, 영어 소문자, 공백/특수문자 → 하이픈
    slug = re.sub(r'[^\w가-힣]+', '-', clean.lower()).strip('-')
    # 너무 길면 자르기
    if len(slug) > 50:
        slug = slug[:50].rstrip('-')
    return slug


def generate_adr(commit, adr_num):
    """커밋에서 ADR 초안을 생성한다."""
    # 접두사에서 결정 유형 판단
    msg = commit['message']
    if msg.lower().startswith('feat:'):
        decision_type = '새 기능 도입'
    elif msg.lower().startswith('fix:'):
        decision_type = '버그 수정'
    elif msg.lower().startswith('refactor:'):
        decision_type = '리팩터링'
    elif msg.lower().startswith('perf:'):
        decision_type = '성능 개선'
    elif msg.lower().startswith('breaking:'):
        decision_type = '호환성 변경'
    else:
        decision_type = '기술 결정'

    # 접두사 제거한 제목
    clean_title = re.sub(r'^(feat|fix|refactor|perf|breaking):\s*', '', msg).strip()
    slug = slugify(msg)
    filename = f'{adr_num:03d}-{slug}.md'

    # 커밋 상세 정보 (변경 파일 목록)
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
        files_str += f' 외 {len(changed_files) - 5}개'

    content = f"""# ADR-{adr_num:03d}: {clean_title}

- 날짜: {commit['date']}
- 상태: 채택됨
- 커밋: `{commit['hash'][:8]}`
- 결정: {clean_title} ({decision_type})
- 이유:
  - (자동 생성됨 — cc가 상세 이유를 보충해야 함)
  - 변경 파일: {files_str if files_str else '(확인 필요)'}
- 대안:
  - (자동 생성됨 — cc가 검토한 대안을 보충해야 함)
- 결과:
  - 커밋 `{commit['hash'][:8]}`로 구현됨.

## Simondon Mapping
<!-- TODO: cc가 시몽동 매핑을 채워야 함 -->
이 결정이 시몽동의 어떤 원리를 구현하는가: (TODO — cc가 채울 것)
"""
    return filename, content


def update_index(new_adrs):
    """INDEX.md에 새 ADR 항목을 추가한다."""
    if not os.path.exists(INDEX_FILE):
        print(f"[adr_auto] INDEX.md 없음: {INDEX_FILE}", file=sys.stderr)
        return

    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Superseded 섹션 바로 위에 새 항목 삽입
    superseded_marker = '## Superseded'
    if superseded_marker not in content:
        # Superseded 섹션이 없으면 파일 끝에 추가
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
    parser = argparse.ArgumentParser(description='ADR 자동 생성 — git log 기반')
    parser.add_argument('--since', help='이 날짜 이후 커밋에서 추출 (YYYY-MM-DD)')
    parser.add_argument('--commit', help='특정 커밋 해시')
    parser.add_argument('--count', type=int, default=10, help='최근 N개 커밋 (기본: 10)')
    parser.add_argument('--dry-run', action='store_true', help='생성하지 않고 미리보기만')
    args = parser.parse_args()

    # decisions 디렉토리 확인
    if not os.path.isdir(DECISIONS_DIR):
        print(f"[adr_auto] decisions 디렉토리 없음: {DECISIONS_DIR}", file=sys.stderr)
        sys.exit(1)

    # 1. 커밋 수집
    commits = get_commits(since=args.since, commit=args.commit, count=args.count)
    if not commits:
        print("[adr_auto] 처리할 커밋 없음")
        return

    # 2. 결정 커밋 필터링
    decision_commits = filter_decision_commits(commits)
    if not decision_commits:
        print(f"[adr_auto] {len(commits)}개 커밋 중 결정 사항 없음 (feat:/fix:/refactor:/perf:/breaking: 접두사 필요)")
        return

    # 3. 기존 ADR 로드
    existing_adrs = get_existing_adrs()
    next_num = get_next_adr_number(existing_adrs)

    # 4. 중복 확인 + 생성
    created = []
    skipped = []

    for c in decision_commits:
        is_dup, dup_title, ratio = is_duplicate(c['message'], existing_adrs)
        if is_dup:
            skipped.append((c['message'], dup_title, ratio))
            continue

        filename, content = generate_adr(c, next_num)
        filepath = os.path.join(DECISIONS_DIR, filename)

        # 접두사 제거한 제목
        clean_title = re.sub(r'^(feat|fix|refactor|perf|breaking):\s*', '', c['message']).strip()

        if args.dry_run:
            print(f"[dry-run] ADR-{next_num:03d}: {clean_title}")
            print(f"          파일: {filename}")
            print(f"          커밋: {c['hash'][:8]} ({c['date']})")
            print()
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            created.append((next_num, filename, clean_title, c['date']))
            print(f"[adr_auto] 생성: {filename}")

        # 새로 생성된 ADR도 중복 체크 대상에 추가
        existing_adrs.append({'num': next_num, 'title': f'ADR-{next_num:03d}: {clean_title}', 'filename': filename})
        next_num += 1

    # 5. INDEX.md 갱신
    if created and not args.dry_run:
        update_index(created)
        print(f"[adr_auto] INDEX.md 갱신 완료 ({len(created)}건 추가)")

    # 6. 결과 요약
    print(f"\n[adr_auto] 요약: 커밋 {len(commits)}개 스캔, 결정 {len(decision_commits)}개 감지, "
          f"생성 {len(created)}개, 중복 스킵 {len(skipped)}개")

    if skipped:
        print("\n[adr_auto] 중복으로 스킵:")
        for msg, dup_title, ratio in skipped:
            print(f"  - \"{msg}\" ≈ \"{dup_title}\" (유사도: {ratio:.0%})")

    if created:
        print("\n[adr_auto] TODO: 생성된 ADR의 Simondon Mapping을 cc가 채워야 함")


if __name__ == '__main__':
    main()
