"""
전도(Transduction) 자동 탐지 — T9OS seed prototype for transduction detection
================================================================
새 엔티티가 capture될 때, 기존 엔티티와의 개념 겹침(concept overlap)을
계산하여 구조적 유사성이 높은 엔티티를 자동으로 relate 제안한다.

시몽동의 전도: 한 영역에서 발견된 구조가 차이(disparation)를 매개로
다른 영역에 구조를 형성해 나가는 과정.
"""
import sqlite3
import json
from collections import Counter


def find_transductions(conn, new_concepts, new_text, exclude_id=None, top_k=3, min_score=0.3):
    """
    새 엔티티의 concepts와 text를 기존 DB의 엔티티들과 비교하여
    전도 가능성이 높은 엔티티를 반환한다.

    Returns: [(entity_id, filename, score, shared_concepts), ...]
    """
    if not new_concepts:
        return []

    new_set = set(new_concepts)
    new_text_lower = new_text.lower() if new_text else ""

    rows = conn.execute(
        "SELECT id, filename, concepts, body_preview FROM entities WHERE phase NOT IN ('dissolved', 'sediment')"
    ).fetchall()

    candidates = []
    for row in rows:
        if exclude_id and row["id"] == exclude_id:
            continue

        # 기존 엔티티의 concepts 파싱
        existing_concepts = _parse_concepts(row["concepts"])
        if not existing_concepts:
            continue

        existing_set = set(existing_concepts)

        # 개념 겹침 점수 (Jaccard similarity)
        intersection = new_set & existing_set
        union = new_set | existing_set
        if not union:
            continue

        jaccard = len(intersection) / len(union)

        # 보너스: 겹치는 개념이 2개 이상이면 가산 보너스
        bonus = 0
        if len(intersection) >= 2:
            bonus += 0.15

        # 보너스: 서로 다른 도메인에서 온 개념이 겹치면 (전도적 학습)
        domain_diversity = _domain_diversity(intersection)
        if domain_diversity > 1:
            bonus += 0.05 * domain_diversity

        # 최종 점수: 0~1 범위로 클램핑
        jaccard = min(jaccard + bonus, 1.0)

        if jaccard >= min_score:
            candidates.append((
                row["id"],
                row["filename"],
                round(jaccard, 3),
                sorted(intersection)
            ))

    # 점수 내림차순, top_k
    candidates.sort(key=lambda x: -x[2])
    return candidates[:top_k]


# 개념 → 도메인 매핑 (다대일: 여러 개념이 같은 도메인에 속해야 의미 있음)
CONCEPT_DOMAIN = {
    "create": "making",      # 만드는 것
    "solve": "making",       # 만드는 것 (같은 도메인)
    "explore": "thinking",   # 탐구하는 것
    "become": "thinking",    # 성장하는 것 (같은 도메인)
    "earn": "acting",        # 행동하는 것
    "express": "acting",     # 표현하는 것 (같은 도메인)
}


def _domain_diversity(concepts):
    """겹치는 개념들이 몇 개의 서로 다른 도메인에 걸쳐있는지."""
    domains = set()
    for c in concepts:
        d = CONCEPT_DOMAIN.get(c, "other")
        domains.add(d)
    return len(domains)


def _parse_concepts(concepts_str):
    """DB에서 concepts를 파싱. JSON list 또는 comma-separated string."""
    if not concepts_str:
        return []
    try:
        parsed = json.loads(concepts_str)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    # comma-separated fallback
    if isinstance(concepts_str, str):
        return [c.strip() for c in concepts_str.split(",") if c.strip()]
    return []


def format_transduction_report(results):
    """전도 탐지 결과를 사람이 읽을 수 있는 포맷으로."""
    if not results:
        return ""

    lines = ["  [전도 탐지] 구조적 유사 엔티티 발견:"]
    for eid, filename, score, shared in results:
        name = filename[:50] if len(filename) > 50 else filename
        concepts_str = ", ".join(shared)
        lines.append(f"    [{eid}] {name} (유사도={score}, 공유개념={concepts_str})")
    lines.append("    → relate <id1> <id2>로 연결 가능")
    return "\n".join(lines)
