#!/usr/bin/env python3
"""T9 OS v1→v2 마이그레이션 검증 스크립트.
매 Phase 완료 후 실행하여 데이터 무결성 확인."""

import sqlite3
import sys
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '.t9.db')
SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), '..', '.t9_snapshot.json')

# 동적 스냅샷: 파일에서 로드하거나 기본값 사용
def load_snapshot():
    if os.path.exists(SNAPSHOT_PATH):
        import json
        with open(SNAPSHOT_PATH) as f:
            return json.load(f)
    # 폴백: v1 초기 스냅샷 (2026-03-20)
    return {
        'total_entities': 531,
        'transitions': 231,
        'relations': 4,
        'tables': ['entities', 'transitions', 'entities_fts', 'relates',
                   'sessions', 'messages', 'file_locks'],
        'snapshot_date': '2026-03-20'
    }

def save_snapshot():
    """현재 상태를 스냅샷으로 저장."""
    import json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    snapshot = {
        'total_entities': c.execute('SELECT COUNT(*) FROM entities').fetchone()[0],
        'transitions': c.execute('SELECT COUNT(*) FROM transitions').fetchone()[0],
        'relations': c.execute('SELECT COUNT(*) FROM relates').fetchone()[0],
        'tables': ['entities', 'transitions', 'entities_fts', 'relates',
                   'sessions', 'messages', 'file_locks'],
        'snapshot_date': datetime.now().strftime('%Y-%m-%d')
    }
    conn.close()
    with open(SNAPSHOT_PATH, 'w') as f:
        json.dump(snapshot, f, indent=2)
    print(f"Snapshot saved: {SNAPSHOT_PATH}")

V1_SNAPSHOT = load_snapshot()

def verify():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    errors = []
    warnings = []

    # 1. Entity count (should never decrease)
    total = c.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
    if total < V1_SNAPSHOT['total_entities']:
        errors.append(f"Entity count decreased: {V1_SNAPSHOT['total_entities']} → {total}")
    elif total > V1_SNAPSHOT['total_entities']:
        warnings.append(f"Entity count increased: {V1_SNAPSHOT['total_entities']} → {total} (OK if new captures)")

    # 2. Phase distribution (total should be preserved, individual phases may shift)
    phases = dict(c.execute('SELECT phase, COUNT(*) FROM entities GROUP BY phase').fetchall())
    total_by_phase = sum(phases.values())
    if total_by_phase < V1_SNAPSHOT['total_entities']:
        errors.append(f"Total by phase decreased: {V1_SNAPSHOT['total_entities']} → {total_by_phase}")
    # Note: individual phase counts may shift due to Pipeline Composer auto-classification

    # 3. Tables exist
    tables = [t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for t in V1_SNAPSHOT['tables']:
        if t not in tables:
            errors.append(f"Table missing: {t}")

    # 4. FTS works
    try:
        fts = c.execute("SELECT COUNT(*) FROM entities_fts WHERE entities_fts MATCH 'T9'").fetchone()[0]
        if fts == 0:
            warnings.append("FTS returned 0 results for 'T9' (was 249)")
    except Exception as e:
        errors.append(f"FTS broken: {e}")

    # 5. Transitions preserved
    trans = c.execute('SELECT COUNT(*) FROM transitions').fetchone()[0]
    if trans < V1_SNAPSHOT['transitions']:
        errors.append(f"Transitions lost: {V1_SNAPSHOT['transitions']} → {trans}")

    # 6. Relations preserved
    rels = c.execute('SELECT COUNT(*) FROM relates').fetchone()[0]
    if rels < V1_SNAPSHOT['relations']:
        errors.append(f"Relations lost: {V1_SNAPSHOT['relations']} → {rels}")

    conn.close()

    # Report
    print("=" * 50)
    print("T9 OS Migration Verification")
    print("=" * 50)
    print(f"Entities: {total} (v1: {V1_SNAPSHOT['total_entities']})")
    print(f"Transitions: {trans} (v1: {V1_SNAPSHOT['transitions']})")
    print(f"Relations: {rels} (v1: {V1_SNAPSHOT['relations']})")

    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    if not errors and not warnings:
        print("\n✅ ALL CHECKS PASSED")

    return len(errors) == 0

if __name__ == '__main__':
    ok = verify()
    sys.exit(0 if ok else 1)
