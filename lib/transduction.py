"""
Transduction auto-detection — seed prototype for cross-domain pattern transfer
================================================================
When a new entity is captured, compute concept overlap with existing entities
and auto-suggest relations to structurally similar entities.

Simondon's transduction: structure found in one domain propagates through
disparation to form structure in another domain.
"""
import sqlite3
import json
from collections import Counter


def find_transductions(conn, new_concepts, new_text, exclude_id=None, top_k=3, min_score=0.3):
    """
    Compare new entity's concepts and text with existing DB entities
    and return entities with high transduction potential.

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

        # existing concepts
        existing_concepts = _parse_concepts(row["concepts"])
        if not existing_concepts:
            continue

        existing_set = set(existing_concepts)

        # score (Jaccard similarity)
        intersection = new_set & existing_set
        union = new_set | existing_set
        if not union:
            continue

        jaccard = len(intersection) / len(union)

        #
        bonus = 0
        if len(intersection) >= 2:
            bonus += 0.15

        # : (transductive learning)
        domain_diversity = _domain_diversity(intersection)
        if domain_diversity > 1:
            bonus += 0.05 * domain_diversity

        # final score: 0~1 scope
        jaccard = min(jaccard + bonus, 1.0)

        if jaccard >= min_score:
            candidates.append((
                row["id"],
                row["filename"],
                round(jaccard, 3),
                sorted(intersection)
            ))

    # score , top_k
    candidates.sort(key=lambda x: -x[2])
    return candidates[:top_k]


# → mapping (: )
CONCEPT_DOMAIN = {
    "create": "making",
    "solve": "making",
    "explore": "thinking",
    "become": "thinking",
    "earn": "acting",
    "express": "acting",
}


def _domain_diversity(concepts):
    """."""
    domains = set()
    for c in concepts:
        d = CONCEPT_DOMAIN.get(c, "other")
        domains.add(d)
    return len(domains)


def _parse_concepts(concepts_str):
    """DBconcepts. JSON list comma-separated string."""
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
    """result."""
    if not results:
        return ""

    lines = ["  [ ] structure   found:"]
    for eid, filename, score, shared in results:
        name = filename[:50] if len(filename) > 50 else filename
        concepts_str = ", ".join(shared)
        lines.append(f"    [{eid}] {name} (={score}, ={concepts_str})")
    lines.append("    → relate <id1> <id2> connection ")
    return "\n".join(lines)
