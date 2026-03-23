#!/usr/bin/env python3
"""T9 OS v2 — Pipeline Composer v0.1
전개체(preindividual) 자동 분류 + 라우팅.
247개 적체 해소를 위한 자동 트리아지 엔진.

역할 분리 (t9_auto.py와의 관계):
- pipeline_composer: 라우팅 (어디로 보낼지 결정) + urgency 설정
- t9_auto.py: concepts 추출 + 프로젝트 분류 (Gemini 기반)
- 동시 실행 시: composer 먼저 → auto가 concepts만 보충

분류 규칙 (deterministic, 빠름):
1. 마감일 키워드 → deadline_notify + urgency 설정
2. 일정/캘린더 키워드 → calendar_sync
3. 코드/기술 키워드 → 코드 세션 라우팅
4. 감정/고민 키워드 → 설계자 대화 플래그
5. 리서치 키워드 → t9-research
6. 나머지 → 단순 기록 (이미 capture됨)

Usage:
    python3 T9OS/pipes/pipeline_composer.py              # 전체 preindividual 분류
    python3 T9OS/pipes/pipeline_composer.py --dry-run     # 미리보기 (실행 안 함)
    python3 T9OS/pipes/pipeline_composer.py --limit 10    # 10개만
"""

import sqlite3
import os
import sys
import re
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '.t9.db')

# 분류 규칙 (패턴 → 카테고리)
RULES = [
    {
        'name': 'deadline',
        'patterns': [
            r'마감|deadline|~까지|D-\d|제출|기한|due|until|시험|중간고사|기말',
            r'\d{1,2}/\d{1,2}|\d{1,2}월\s*\d{1,2}일',
        ],
        'action': 'deadline_notify',
        'urgency': 'high',
    },
    {
        'name': 'calendar',
        'patterns': [r'일정|캘린더|약속|미팅|회의|수업|강의|zoom|시간표|몇시'],
        'action': 'calendar_sync',
        'urgency': 'mid',
    },
    {
        'name': 'code',
        'patterns': [r'코드|버그|에러|배포|deploy|git|API|함수|스크립트|파이프라인|구현|빌드'],
        'action': 'code_session',
        'urgency': 'mid',
    },
    {
        'name': 'research',
        'patterns': [r'리서치|조사|논문|연구|분석|데이터|통계|검색해|찾아봐|알아봐'],
        'action': 't9_research',
        'urgency': 'mid',
    },
    {
        'name': 'emotion',
        'patterns': [r'(?<!\w)(불안하|걱정[되이]|스트레스\s*받|힘들[어다]|지치|모르겠|어떡해|고민[이중]|답답[하해]|짜증[나이])'],
        'action': 'dialogue',
        'urgency': 'low',
    },
    {
        'name': 'idea',
        'patterns': [r'아이디어|영감|갑자기|생각|떠오른|혹시|만약에|재밌|신기'],
        'action': 'archive',
        'urgency': 'low',
    },
]

def classify(text: str) -> dict:
    """텍스트를 규칙 기반으로 분류."""
    text_lower = text.lower()
    matches = []

    for rule in RULES:
        for pattern in rule['patterns']:
            if re.search(pattern, text_lower):
                matches.append(rule)
                break

    if not matches:
        return {'name': 'archive', 'action': 'archive', 'urgency': 'low'}

    # 우선순위: deadline > calendar > code > research > emotion > idea
    priority = ['deadline', 'calendar', 'code', 'research', 'emotion', 'idea']
    matches.sort(key=lambda m: priority.index(m['name']) if m['name'] in priority else 99)

    return matches[0]

def process_preindividuals(dry_run=False, limit=None):
    """preindividual 엔티티를 분류하고 라우팅."""
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

        # urgency 업데이트
        if classification['urgency'] == 'high' and row['urgency'] != 'high':
            c.execute("UPDATE entities SET urgency = 'high' WHERE id = ?", (row['id'],))

        # 메타데이터에 분류 결과 저장
        meta['auto_classified'] = classification['name']
        meta['auto_action'] = classification['action']
        meta['classified_at'] = datetime.now().isoformat()
        c.execute("UPDATE entities SET metadata = ? WHERE id = ?",
                  (json.dumps(meta, ensure_ascii=False), row['id']))

        # tension_detected로 전이 (분류됨 = 긴장 감지)
        if classification['name'] in ('deadline', 'code', 'research'):
            c.execute("UPDATE entities SET phase = 'tension_detected' WHERE id = ? AND phase = 'preindividual'",
                      (row['id'],))
            c.execute("INSERT INTO transitions (entity_id, from_phase, to_phase, timestamp, reason) VALUES (?, 'preindividual', 'tension_detected', ?, ?)",
                      (row['id'], datetime.now().isoformat(), f"Pipeline Composer: {classification['name']}"))

    if not dry_run:
        conn.commit()
    conn.close()

    # 결과 출력
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
