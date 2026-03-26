"""
전도(Transduction) 자동 탐지 — ODNAR 핵심 기능의 seed 프로토타입
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

    v2: 벡터 임베딩 기반 탐색 (gravity.py). Jaccard은 fallback.

    Returns: [(entity_id, filename, score, shared_concepts), ...]
    """
    # 1차: 벡터 임베딩 기반 (공간에서의 거리)
    try:
        from lib.gravity import embed, find_neighbors
        vec = embed(new_text) if new_text else None
        if vec is not None:
            neighbors = find_neighbors(conn, vec, exclude_id=exclude_id, top_k=top_k, threshold=min_score)
            if neighbors:
                results = []
                for n in neighbors:
                    # 공유 개념 추출 (있으면)
                    shared = []
                    if new_concepts:
                        existing = _parse_concepts(
                            conn.execute("SELECT concepts FROM entities WHERE id=?", (n["id"],)).fetchone()[0]
                        ) if conn.execute("SELECT concepts FROM entities WHERE id=?", (n["id"],)).fetchone() else []
                        shared = sorted(set(new_concepts) & set(existing))
                    results.append((n["id"], n["filename"], round(n["similarity"], 3), shared))
                return results
    except Exception:
        pass  # fallback to Jaccard

    # 2차 (fallback): Jaccard 기반 개념 겹침
    if not new_concepts:
        return []

    new_set = set(new_concepts)

    rows = conn.execute(
        "SELECT id, filename, concepts, body_preview FROM entities WHERE phase NOT IN ('dissolved', 'sediment')"
    ).fetchall()

    candidates = []
    for row in rows:
        if exclude_id and row["id"] == exclude_id:
            continue
        existing_concepts = _parse_concepts(row["concepts"])
        if not existing_concepts:
            continue
        existing_set = set(existing_concepts)
        intersection = new_set & existing_set
        union = new_set | existing_set
        if not union:
            continue
        jaccard = len(intersection) / len(union)
        bonus = 0
        if len(intersection) >= 2:
            bonus += 0.15
        domain_diversity = _domain_diversity(intersection)
        if domain_diversity > 1:
            bonus += 0.05 * domain_diversity
        jaccard = min(jaccard + bonus, 1.0)
        if jaccard >= min_score:
            candidates.append((row["id"], row["filename"], round(jaccard, 3), sorted(intersection)))

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
