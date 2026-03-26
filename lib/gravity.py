"""
중력 엔진 (Gravitational Individuation Engine)
===============================================
시몽동의 개체화를 벡터 공간에서 구현한다.

Phase 2: 충돌 + NLI + 파동 전파.
Phase 1 (vec.py): 공간 인프라 (임베딩 생성/저장/검색).

원리 (한빈 + cc 설계 대화, 2026-03-26):
- 열운동 = 한빈+cc 활동 (이미 존재)
- 공간 = 벡터 임베딩 (vec.py가 제공)
- 충돌 = 공간에서 가까운 전개체끼리 만남 (이 모듈)
- 개체화 = 충돌 시 disparation 감지 → 자동 전이

"사과는 체크하지 않아도 떨어진다." — capture 순간 중력이 작동.
"자연은 기록하지 않는다." — 정보는 사물이 아니라 조작(operation).
"완전한 반대는 같은 선 위에서 수렴한다." — NLI로 모순 탐지.
"""
import logging
import numpy as np

_log = logging.getLogger("gravity")


# ── 이웃 탐색 (vec.py의 sqlite-vec 활용) ─────────────────────

def find_neighbors(conn, entity_id=None, text=None, top_k=10, threshold=0.25):
    """
    벡터 공간에서 이웃 탐색.
    entity_id 기반 (DB에 이미 임베딩 있을 때) 또는 text 기반 (새 텍스트).

    Returns: [{"id": int, "filename": str, "similarity": float, "body_preview": str}, ...]
    """
    try:
        from lib.vec import search_vectors, get_query_embedding, get_embedding
    except ImportError:
        return []

    # 쿼리 벡터 결정
    if text:
        query_vec = get_query_embedding(text)
    elif entity_id:
        # entity_vectors에서 가져오기
        try:
            from lib.vec import _serialize_f32
            row = conn.execute(
                "SELECT embedding FROM entity_vectors WHERE entity_id=?", (entity_id,)
            ).fetchone()
            if row:
                query_vec = list(np.frombuffer(row[0], dtype=np.float32))
            else:
                return []
        except Exception:
            return []
    else:
        return []

    if not query_vec:
        return []

    # sqlite-vec KNN 검색
    raw_results = search_vectors(conn, query_vec, limit=top_k + 5)  # 여유분
    if not raw_results:
        return []

    # distance → similarity 변환 + 필터링
    results = []
    for eid, distance in raw_results:
        if entity_id and eid == entity_id:
            continue
        # sqlite-vec distance는 L2. 코사인 유사도 근사: 1 - (d^2 / 2)
        similarity = max(0, 1 - (distance ** 2 / 2)) if distance < 2 else 0
        if similarity >= threshold:
            results.append({"id": eid, "similarity": round(float(similarity), 4)})

    results.sort(key=lambda x: -x["similarity"])
    results = results[:top_k]

    # DB에서 파일명/프리뷰 보강
    if results:
        id_list = [r["id"] for r in results]
        placeholders = ",".join("?" * len(id_list))
        rows = conn.execute(
            f"SELECT id, filename, body_preview, phase, filepath FROM entities WHERE id IN ({placeholders})",
            id_list
        ).fetchall()
        info = {r["id"]: dict(r) for r in rows}
        for r in results:
            row_info = info.get(r["id"], {})
            r["filename"] = row_info.get("filename", "")
            r["body_preview"] = row_info.get("body_preview", "")
            r["phase"] = row_info.get("phase", "")
            r["filepath"] = row_info.get("filepath", "")

    return results


# ── NLI Disparation 탐지 ────────────────────────────────────
_nli_model = None


def _get_nli_model():
    """DeBERTa-v3-base NLI 모델 lazy 로드."""
    global _nli_model
    if _nli_model is None:
        try:
            from sentence_transformers import CrossEncoder
            _nli_model = CrossEncoder("cross-encoder/nli-deberta-v3-base")
        except Exception as e:
            _log.warning("NLI model load failed: %s", e)
            return None
    return _nli_model


def detect_disparation(pairs: list[tuple[str, str]]) -> list[dict]:
    """
    NLI 크로스인코더로 텍스트 쌍의 모순/수반/중립 탐지.

    시몽동: disparation = 두 비양립적 질서 사이의 긴장.
    한빈 반대이론: 완전한 반대는 같은 선 위에서 수렴.

    Returns: [{"contradiction": float, "entailment": float, "neutral": float, "label": str}, ...]
    """
    if not pairs:
        return []
    model = _get_nli_model()
    if model is None:
        return [{"contradiction": 0, "entailment": 0, "neutral": 0, "label": "unknown"}] * len(pairs)
    try:
        truncated_pairs = [(a[:500], b[:500]) for a, b in pairs]
        scores = model.predict(truncated_pairs)
        results = []
        label_map = {0: "contradiction", 1: "entailment", 2: "neutral"}
        for score in scores:
            label = label_map[int(np.argmax(score))]
            results.append({
                "contradiction": float(score[0]),
                "entailment": float(score[1]),
                "neutral": float(score[2]),
                "label": label,
            })
        return results
    except Exception as e:
        _log.warning("NLI inference failed: %s", e)
        return [{"contradiction": 0, "entailment": 0, "neutral": 0, "label": "unknown"}] * len(pairs)


# ── 파동 전파 (de proche en proche) ─────────────────────────

def propagate(conn, entity_id, max_new_relates=3):
    """
    시몽동의 전도: 이미 구조화된 영역이 인접 미구조화 영역의 구조화 원리가 된다.
    "chaque couche moléculaire déjà constituée sert de base organisatrice..."

    entity_id의 relate 대상들 중, 서로 아직 연결 안 된 이웃끼리 자동 relate.
    depth=1 (한 홉), max_new_relates로 폭발 방지.
    """
    related = conn.execute(
        "SELECT target_id FROM relates WHERE source_id=? "
        "UNION SELECT source_id FROM relates WHERE target_id=?",
        (entity_id, entity_id)
    ).fetchall()
    related_ids = [r[0] for r in related if r[0] != entity_id]
    if len(related_ids) < 2:
        return []

    new_relates = []
    for i in range(len(related_ids)):
        if len(new_relates) >= max_new_relates:
            break
        for j in range(i + 1, len(related_ids)):
            if len(new_relates) >= max_new_relates:
                break
            a, b = related_ids[i], related_ids[j]
            exists = conn.execute(
                "SELECT 1 FROM relates WHERE (source_id=? AND target_id=?) OR (source_id=? AND target_id=?)",
                (a, b, b, a)
            ).fetchone()
            if not exists:
                # sqlite-vec로 두 엔티티 간 거리 확인
                neighbors_a = find_neighbors(conn, entity_id=a, top_k=20, threshold=0.3)
                b_in_neighbors = any(n["id"] == b for n in neighbors_a)
                if b_in_neighbors:
                    from datetime import datetime
                    sim = next((n["similarity"] for n in neighbors_a if n["id"] == b), 0)
                    conn.execute(
                        "INSERT OR IGNORE INTO relates (source_id, target_id, direction, description, created_at) "
                        "VALUES (?, ?, 'bidirectional', ?, ?)",
                        (a, b, f"propagation: sim={sim:.2f} via [{entity_id}]",
                         datetime.now().isoformat())
                    )
                    new_relates.append((a, b, sim))
    if new_relates:
        conn.commit()
    return new_relates


# ── 중력 시퀀스 (capture에서 호출) ──────────────────────────

def gravitational_capture(conn, entity_id, text, filepath_rel):
    """
    capture 직후 호출. 중력 = disparation이 힘.
    1. embed → 좌표 부여 (vec.py)
    2. find_neighbors → 이웃 탐색 (충돌)
    3. detect_disparation → 모순 탐지 (NLI)
    4. auto-relate → disparation/resonance 연결
    5. auto-transition → tension_detected
    6. propagate → 파동 전파

    Returns: dict with summary
    """
    from datetime import datetime
    result = {"embedded": False, "neighbors": 0, "relates": 0, "phase_changed": False, "propagated": 0}

    # 1. 임베딩 (vec.py 사용)
    try:
        from lib.vec import get_embedding, build_embed_text, upsert_vector

        # concepts, phase 가져오기
        row = conn.execute("SELECT body_preview, concepts, phase FROM entities WHERE id=?", (entity_id,)).fetchone()
        if not row:
            return result
        embed_text = build_embed_text(text[:2000], row["concepts"] or "", row["phase"] or "")
        vec = get_embedding(embed_text)
        if vec is None:
            return result

        # entity_vectors에 저장
        upsert_vector(conn, entity_id, vec)
        # entities.embedding BLOB에도 저장 (gravity fallback용)
        vec_np = np.array(vec, dtype=np.float32)
        conn.execute("UPDATE entities SET embedding=? WHERE id=?", (vec_np.tobytes(), entity_id))
        result["embedded"] = True
    except Exception as e:
        _log.warning("gravity embed failed: %s", e)
        return result

    # 2. 이웃 탐색
    neighbors = find_neighbors(conn, text=text, top_k=10, threshold=0.25)
    # 자기 자신 제외
    neighbors = [n for n in neighbors if n["id"] != entity_id]
    result["neighbors"] = len(neighbors)
    if not neighbors:
        conn.commit()
        return result

    # 3. NLI — 상위 5개만 (비용/속도 제어)
    top_neighbors = neighbors[:5]
    pairs = [(text[:500], n.get("body_preview", "")[:500]) for n in top_neighbors]
    valid_pairs = [(i, p) for i, p in enumerate(pairs) if p[1].strip()]
    if not valid_pairs:
        conn.commit()
        return result

    nli_results = detect_disparation([p for _, p in valid_pairs])

    # 4. 자동 relate — disparation forte/faible 분류
    # 시몽동: "deux ensembles jumeaux non totalement superposables"
    # 양안시: 거의 같지만(높은 유사도) 겹칠 수 없는(contradiction) 것이 진짜 disparation.
    # 한빈 반대이론: "완전한 반대는 같은 선 위에서 수렴한다"
    relate_count = 0
    for (orig_idx, _), nli in zip(valid_pairs, nli_results):
        n = top_neighbors[orig_idx]
        sim = n.get("similarity", 0)
        desc = None

        if nli["label"] == "contradiction" and nli["contradiction"] > 0.4:
            if sim > 0.5:
                # disparation_forte: 가깝지만 모순 = 같은 선의 양 끝
                # 이것이 dimension nouvelle를 열 잠재력이 가장 높다
                desc = f"disparation_forte: sim={sim:.2f} contr={nli['contradiction']:.2f}"
                print(f"  [disparation forte] [{n['id']}] {n['filename'][:40]} (sim={sim:.2f}, contr={nli['contradiction']:.2f})")
            else:
                # disparation_faible: 멀면서 모순 = 다른 영역의 충돌
                desc = f"disparation_faible: sim={sim:.2f} contr={nli['contradiction']:.2f}"
                print(f"  [disparation faible] [{n['id']}] {n['filename'][:40]} (sim={sim:.2f}, contr={nli['contradiction']:.2f})")
        elif nli["label"] == "entailment" and nli["entailment"] > 0.7:
            desc = f"resonance: entailment={nli['entailment']:.2f}"
            print(f"  [resonance] [{n['id']}] {n['filename'][:40]}")
        elif nli["label"] == "neutral" and nli["neutral"] > 0.6 and sim > 0.5:
            # vertical_tension: 가깝지만 NLI 판단 불가 = 두 크기 질서가 소통 없이 공존
            # 시몽동: "deux ordres de grandeur et l'absence de communication"
            # 모순도 수반도 아닌, 서로 말이 안 통하는 상태 = 준안정성의 전제 조건
            desc = f"vertical_tension: sim={sim:.2f} neutral={nli['neutral']:.2f}"
            print(f"  [vertical tension] [{n['id']}] {n['filename'][:40]} (sim={sim:.2f}, neutral={nli['neutral']:.2f})")

        if desc:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO relates (source_id, target_id, direction, description, created_at) "
                    "VALUES (?, ?, 'bidirectional', ?, ?)",
                    (entity_id, n["id"], desc, datetime.now().isoformat())
                )
                relate_count += 1
            except Exception:
                pass
    result["relates"] = relate_count

    # 5. 자동 위상 전이 (preindividual → tension_detected)
    if relate_count > 0:
        current = conn.execute("SELECT phase FROM entities WHERE id=?", (entity_id,)).fetchone()
        if current and current["phase"] == "preindividual":
            conn.execute("UPDATE entities SET phase='tension_detected' WHERE id=?", (entity_id,))
            conn.execute(
                "INSERT INTO transitions (entity_id, from_phase, to_phase, timestamp, reason) VALUES (?,?,?,?,?)",
                (entity_id, "preindividual", "tension_detected",
                 datetime.now().isoformat(), f"gravity: {relate_count} relates")
            )
            result["phase_changed"] = True
            print(f"  [phase] preindividual → tension_detected (gravity: {relate_count} relates)")

    # 6. 파동 전파
    if relate_count > 0:
        wave = propagate(conn, entity_id, max_new_relates=3)
        result["propagated"] = len(wave)
        for a, b, sim in wave:
            print(f"  [wave] [{a}] ↔ [{b}] (sim={sim:.2f})")

    conn.commit()
    return result


# ── 소급 결정화 (기존 전개체에 중력 적용) ───────────────────

def retroactive_crystallization(conn, max_rounds=10, batch_size=20):
    """
    시몽동: "chaque couche moléculaire déjà constituée
             sert de base structurante à la couche en train de se former"

    이미 구조화된 엔티티(씨앗)에서 시작하여,
    가장 가까운 preindividual로 중력을 전파한다.
    라운드마다 "결정 표면"이 넓어지며 가속한다 (structure réticulaire amplifiante).

    Returns: {"rounds": int, "total_transitions": int, "total_relates": int}
    """
    from datetime import datetime
    summary = {"rounds": 0, "total_transitions": 0, "total_relates": 0}

    for round_num in range(max_rounds):
        # 결정 표면 = 이미 구조화된 것 (씨앗)
        surface = conn.execute(
            "SELECT id, body_preview, filepath FROM entities "
            "WHERE phase IN ('tension_detected', 'individuating', 'stabilized') "
            "AND embedding IS NOT NULL"
        ).fetchall()
        if not surface:
            # 씨앗이 없으면 첫 번째 라운드: stabilized/archived 중 relate가 있는 것
            surface = conn.execute(
                "SELECT DISTINCT e.id, e.body_preview, e.filepath FROM entities e "
                "JOIN relates r ON e.id = r.source_id OR e.id = r.target_id "
                "WHERE e.embedding IS NOT NULL LIMIT 50"
            ).fetchall()
            if not surface:
                break

        # 이번 라운드 전이 수
        round_transitions = 0
        round_relates = 0

        for seed in surface[:batch_size]:
            # 씨앗에서 가장 가까운 preindividual 찾기
            neighbors = find_neighbors(conn, entity_id=seed["id"], top_k=5, threshold=0.3)
            for n in neighbors:
                if n.get("phase") != "preindividual":
                    continue
                # 중력 적용
                preview = n.get("body_preview", "")
                if not preview:
                    continue
                g = gravitational_capture(conn, n["id"], preview, n.get("filepath", ""))
                if g["phase_changed"]:
                    round_transitions += 1
                round_relates += g["relates"]

        summary["rounds"] = round_num + 1
        summary["total_transitions"] += round_transitions
        summary["total_relates"] += round_relates

        print(f"  [crystallization] round {round_num+1}: {round_transitions} transitions, {round_relates} relates")

        if round_transitions == 0:
            break  # 포화 — 더 이상 결정화할 수 없음

    return summary
