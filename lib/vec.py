"""T9 OS 벡터 검색 — sqlite-vec + Gemini gemini-embedding-001

Phase 1: 공간 인프라. 벡터 저장/검색만 구현.
Phase 2 (de73 담당): 충돌 → 자동 개체화, NLI 모순탐지.
"""

import json, urllib.request, logging, struct, time

_log = logging.getLogger("t9_vec")

# ─── Gemini Embedding API ─────────────────────────────────────────────────

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 3072

_GEMINI_KEY = None

def _get_key():
    global _GEMINI_KEY
    if _GEMINI_KEY is not None:
        return _GEMINI_KEY
    try:
        from lib.config import GEMINI_KEY
        _GEMINI_KEY = GEMINI_KEY
    except Exception:
        import os
        _GEMINI_KEY = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
    return _GEMINI_KEY

def _embed_url():
    return f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:embedContent?key={_get_key()}"

def _batch_url():
    return f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:batchEmbedContents?key={_get_key()}"

# ─── sqlite-vec 게이트 ────────────────────────────────────────────────────

_VEC_AVAILABLE = None

def vec_available(conn) -> bool:
    """sqlite-vec 로드 가능 여부 (캐싱)."""
    global _VEC_AVAILABLE
    if _VEC_AVAILABLE is not None:
        return _VEC_AVAILABLE
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.execute("SELECT * FROM entity_vectors LIMIT 0")
        _VEC_AVAILABLE = True
    except Exception:
        _VEC_AVAILABLE = False
    return _VEC_AVAILABLE

def load_vec(conn):
    """sqlite-vec 확장 로드. get_db에서 호출."""
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception:
        pass

# ─── 임베딩 입력 구성 (시몽동 철학 반영) ──────────────────────────────────

def build_embed_text(body_preview: str, concepts: str = "", phase: str = "") -> str:
    """임베딩 입력 텍스트 구성. concepts+phase를 포함해 벡터 공간에 위상을 녹인다."""
    parts = []
    if concepts:
        try:
            c = json.loads(concepts) if concepts.startswith("[") else [concepts]
            parts.append(f"[concepts: {', '.join(c)}]")
        except Exception:
            parts.append(f"[concepts: {concepts}]")
    if phase:
        parts.append(f"[phase: {phase}]")
    parts.append((body_preview or "")[:2000])
    return " ".join(parts)

# ─── 임베딩 생성 ──────────────────────────────────────────────────────────

def get_embedding(text: str) -> list[float] | None:
    """단일 텍스트 임베딩 (문서 저장용). 실패 시 None."""
    key = _get_key()
    if not key or not text.strip():
        return None
    body = json.dumps({
        "model": f"models/{EMBED_MODEL}",
        "content": {"parts": [{"text": text[:2000]}]},
        "taskType": "RETRIEVAL_DOCUMENT"
    }).encode()
    req = urllib.request.Request(_embed_url(), body, {"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return data["embedding"]["values"]
    except Exception as e:
        _log.warning("embedding failed: %s", e)
        return None

def get_query_embedding(text: str) -> list[float] | None:
    """검색 쿼리용 임베딩. taskType이 다름."""
    key = _get_key()
    if not key or not text.strip():
        return None
    body = json.dumps({
        "model": f"models/{EMBED_MODEL}",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_QUERY"
    }).encode()
    req = urllib.request.Request(_embed_url(), body, {"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return data["embedding"]["values"]
    except Exception as e:
        _log.warning("query embedding failed: %s", e)
        return None

def batch_embeddings(texts: list[str]) -> list[list[float] | None]:
    """배치 임베딩 (최대 100개/요청). batchEmbedContents API."""
    key = _get_key()
    if not key:
        return [None] * len(texts)
    requests = []
    for t in texts:
        requests.append({
            "model": f"models/{EMBED_MODEL}",
            "content": {"parts": [{"text": t[:2000]}]},
            "taskType": "RETRIEVAL_DOCUMENT"
        })
    body = json.dumps({"requests": requests}).encode()
    req = urllib.request.Request(_batch_url(), body, {"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        return [e["values"] for e in data["embeddings"]]
    except Exception as e:
        _log.warning("batch embedding failed: %s", e)
        return [None] * len(texts)

# ─── 벡터 직렬화 ──────────────────────────────────────────────────────────

def _serialize_f32(vec: list[float]) -> bytes:
    """float list → sqlite-vec f32 blob."""
    return struct.pack(f"{len(vec)}f", *vec)

# ─── 벡터 저장/검색 ──────────────────────────────────────────────────────

def upsert_vector(conn, entity_id: int, embedding: list[float]):
    """벡터 저장. 기존 있으면 교체."""
    if not vec_available(conn) or not embedding:
        return
    blob = _serialize_f32(embedding)
    try:
        conn.execute("DELETE FROM entity_vectors WHERE entity_id = ?", (entity_id,))
        conn.execute("INSERT INTO entity_vectors (entity_id, embedding) VALUES (?, ?)",
                     (entity_id, blob))
    except Exception as e:
        _log.warning("vector upsert failed [%d]: %s", entity_id, e)

def search_vectors(conn, query_embedding: list[float], limit: int = 20) -> list[tuple[int, float]]:
    """벡터 KNN 검색. [(entity_id, distance)] 반환. distance 작을수록 유사."""
    if not vec_available(conn) or not query_embedding:
        return []
    blob = _serialize_f32(query_embedding)
    try:
        rows = conn.execute(
            "SELECT entity_id, distance FROM entity_vectors "
            "WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
            (blob, limit)
        ).fetchall()
        return [(r[0], r[1]) for r in rows]
    except Exception as e:
        _log.warning("vector search failed: %s", e)
        return []

def vector_count(conn) -> int:
    """벡터 저장된 엔티티 수."""
    if not vec_available(conn):
        return 0
    try:
        return conn.execute("SELECT COUNT(*) FROM entity_vectors").fetchone()[0]
    except Exception:
        return 0
