"""
T9 OS Seed — 확장 커맨드 모듈 (t9_seed.py 972줄→500줄 분리)
cmd_reflect, cmd_consolidate, cmd_watch, cmd_history, cmd_relate,
cmd_digest_index, cmd_legacy, cmd_ingest, cmd_resurface, cmd_rebuild_fts, cmd_orphans

순환 import 방지: t9_seed.py를 import하지 않는다.
공통 의존성은 함수 인자 또는 lib.* 에서 가져온다.
"""
import sys, json, sqlite3, time, hashlib, logging
from datetime import datetime, timedelta
from pathlib import Path

from lib.parsers import parse_md, write_md
from lib.config import DB_PATH

_log = logging.getLogger("t9_seed")

# ─── 경로 상수 (t9_seed.py와 동일, 순환 import 방지용 독립 선언) ────
T9 = Path(__file__).resolve().parent.parent
HANBEEN = T9.parent
FIELD = T9 / "field" / "inbox"
MEMORY = T9 / "memory"
SEDIMENT = T9 / "spaces" / "sediment"
LEGACY_DB = T9 / ".t9_legacy.db"
LOGS_DIR = T9 / "logs"
LEARNED_PATH = T9 / "telos" / "LEARNED.md"

SCAN_DIRS = [FIELD, T9/"spaces"/"active", T9/"spaces"/"suspended",
             T9/"spaces"/"archived", SEDIMENT, MEMORY, T9/"artifacts",
             T9/"field"/"impulses", T9/"field"/"scraps", T9/"telos",
             T9/"constitution", T9/"data"/"conversations",
             HANBEEN/".claude"/"session-briefs", T9/"decisions",
             T9/"data"/"composes"]
SCAN_EXTS = {".md", ".docx", ".xlsx", ".pdf", ".hwp", ".txt", ".csv", ".log",
             ".zip", ".jpg", ".jpeg", ".png", ".mp4", ".svg"}


def cmd_reflect(get_db):
    conn = get_db(); now = datetime.now()
    wa = (now-timedelta(days=7)).strftime("%Y-%m-%d")
    print(f"\n  === T9 Reflection ({wa} ~ {now:%Y-%m-%d}) ===\n")
    trans = conn.execute("SELECT t.*,e.filename,e.metadata FROM transitions t JOIN entities e ON t.entity_id=e.id WHERE t.timestamp>=? ORDER BY t.timestamp", (wa,)).fetchall()
    if not trans: print("  전이 없음.\n"); conn.close(); return
    comp = [t for t in trans if t["to_phase"]=="archived"]
    diss = [t for t in trans if t["to_phase"]=="dissolved"]
    susp = [t for t in trans if t["to_phase"]=="suspended"]
    prom = [t for t in trans if t["to_phase"] in ("individuating","stabilized","candidate_generated","tension_detected")]
    print(f"  전이 {len(trans)}건: 완료 {len(comp)}, 폐기 {len(diss)}, 중단 {len(susp)}, 승격 {len(prom)}")
    if comp:
        print("  완료:"); [print(f"    {t['filename'][:50]}") for t in comp]
    if diss:
        print("  폐기:"); [print(f"    {t['filename'][:50]} ({t['reason'] or '-'})") for t in diss]
    sug = []
    if not comp: sug.append("완료 0건 -- WIP 과부하 가능성")
    if len(prom)>=5 and not comp: sug.append("승격만 있고 완료 없음")
    if len(diss)>=3: sug.append(f"폐기 {len(diss)}건 -- scope 축소 검토")
    if sug:
        print("  제안:"); [print(f"    * {s}") for s in sug]
    LEARNED_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = f"\n## 주간 반성 -- {now:%Y-%m-%d}\n- 전이: {len(trans)}건 (완료{len(comp)}/폐기{len(diss)}/중단{len(susp)})\n"
    for s in sug: entry += f"- {s}\n"
    existing = LEARNED_PATH.read_text(encoding="utf-8") if LEARNED_PATH.exists() else "# T9 LEARNED\n\n"
    LEARNED_PATH.write_bytes((existing+entry+"\n").encode("utf-8"))
    print(f"\n  기록: {LEARNED_PATH.relative_to(T9)}\n"); conn.close()


def cmd_consolidate(get_db, fhash, _upsert, _preview_len):
    conn = get_db()
    print(f"\n  === T9 Memory Consolidation ===\n")
    archived = conn.execute("SELECT * FROM entities WHERE phase IN ('archived','dissolved') ORDER BY updated_at DESC").fetchall()
    if not archived: print("  아카이브 없음.\n"); conn.close(); return
    MEMORY.mkdir(parents=True, exist_ok=True)
    groups = {}
    for it in archived:
        # 정규 컬럼 concepts 우선, fallback으로 metadata
        concepts_list = []
        if it["concepts"]:
            try: concepts_list = json.loads(it["concepts"])
            except Exception: pass
        if not concepts_list:
            m = json.loads(it["metadata"]) if it["metadata"] else {}
            concepts_list = m.get("concepts", [])
        key = concepts_list[0] if isinstance(concepts_list, list) and concepts_list else "misc"
        groups.setdefault(key, []).append(it)
    total = 0
    for concept, items in groups.items():
        mp = MEMORY/f"memory_{concept}.md"
        ex = mp.read_text(encoding="utf-8") if mp.exists() else f"# Memory: {concept}\n\n"
        new = [i for i in items if f"<!-- eid:{i['id']} -->" not in ex]
        if not new: continue
        sec = f"\n## 통합 -- {datetime.now():%Y-%m-%d %H:%M}\n\n"
        for i in new:
            sec += f"- <!-- eid:{i['id']} --> **{i['filename']}** ({i['phase']})\n"
            pv = (i["body_preview"] or "")[:80].replace("\n"," ")
            if pv: sec += f"  > {pv}\n"
        mp.write_bytes((ex+sec+"\n").encode("utf-8")); total += len(new)
        print(f"  [{concept}] {len(new)}건 -> memory_{concept}.md")
    for md in MEMORY.glob("*.md"):
        if not md.name.startswith("."):
            try:
                m2, b2 = parse_md(md)
                _upsert(conn, f"memory/{md.name}", md.name, m2.get("phase","stabilized"),
                        json.dumps(m2, ensure_ascii=False), b2[:500], fhash(md))
            except Exception as e:
                _log.debug("consolidate parse failed for %s: %s", md.name, e)
    conn.commit(); conn.close()
    print(f"\n  총 {total}건 통합.\n")


def cmd_watch(get_db, fhash, cmd_reindex, interval=5):
    print(f"\n  === T9 파일 감시 ({interval}초) ===\n  Ctrl+C 종료\n")
    def hmap():
        hm = {}
        for sd in SCAN_DIRS:
            if sd.exists():
                for ext in SCAN_EXTS:
                    for f in sd.rglob(f"*{ext}"):
                        if not f.name.startswith("."): hm[str(f.relative_to(T9))] = fhash(f)
        for ext in SCAN_EXTS:
            for f in T9.glob(f"*{ext}"):
                if not f.name.startswith("."): hm[f.name] = fhash(f)
        return hm
    prev = hmap()
    try:
        while True:
            time.sleep(interval); curr = hmap(); ch = False
            for p,h in curr.items():
                if p not in prev or prev[p]!=h: print(f"  [변경] {p}"); ch=True
            for p in prev:
                if p not in curr: print(f"  [삭제] {p}"); ch=True
            if ch: cmd_reindex()
            prev = curr
    except KeyboardInterrupt: print("\n  감시 종료.\n")


def cmd_history(get_db, eid):
    conn = get_db()
    row = conn.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
    if not row: print(f"  ID {eid} 없음"); conn.close(); return
    print(f"\n  === 전이 이력: [{eid}] {row['filename']} ===")
    print(f"  현재: {row['phase']}  경로: {row['filepath']}")
    if row["created_at"]:
        print(f"  생성: {row['created_at'][:16]}")
    if row["parent_id"]:
        print(f"  부모: [{row['parent_id']}]")
    if row["urgency"]:
        print(f"  긴급: {row['urgency']}")
    if row["concepts"]:
        try:
            c = json.loads(row["concepts"])
            print(f"  개념: {', '.join(c)}")
        except Exception: pass
    m = json.loads(row["metadata"]) if row["metadata"] else {}
    rel = m.get("related_to", [])
    if rel: print(f"  연결 (metadata): {rel}")
    # relates 테이블에서도 조회
    rels = conn.execute(
        "SELECT r.*, e1.filename as src_name, e2.filename as tgt_name "
        "FROM relates r "
        "LEFT JOIN entities e1 ON r.source_id=e1.id "
        "LEFT JOIN entities e2 ON r.target_id=e2.id "
        "WHERE r.source_id=? OR r.target_id=?", (eid, eid)
    ).fetchall()
    if rels:
        print(f"  관계 (transduction):")
        for r in rels:
            arrow = "\u2192" if r["direction"] == "source_to_target" else "\u2194"
            desc = f" ({r['description']})" if r["description"] else ""
            print(f"    [{r['source_id']}] {r['src_name'] or '?'} {arrow} [{r['target_id']}] {r['tgt_name'] or '?'}{desc}")
    ts = conn.execute("SELECT * FROM transitions WHERE entity_id=? ORDER BY timestamp", (eid,)).fetchall()
    if ts:
        print()
        for t in ts:
            print(f"  {t['timestamp'][:16]}  {t['from_phase'] or '(start)'} -> {t['to_phase']}")
            if t["reason"]: print(f"                    사유: {t['reason']}")
    else: print("\n  전이 이력 없음.")
    print(); conn.close()


def cmd_relate(get_db, self_check, id1, id2, direction="bidirectional", description=""):
    """엔티티 연결. transduction 기록 (방향성 지원).

    direction: "bidirectional" | "source_to_target" (id1->id2)
    description: "A의 패턴이 B의 원리가 됨" 같은 설명
    """
    conn = get_db()
    for eid in (id1, id2):
        row = conn.execute("SELECT id FROM entities WHERE id=?", (eid,)).fetchone()
        if not row: print(f"  ID {eid} 없음"); conn.close(); return

    # relates 테이블에 기록 (transduction)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO relates (source_id, target_id, direction, description, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (id1, id2, direction, description, datetime.now().isoformat())
        )
    except sqlite3.IntegrityError:
        conn.execute(
            "UPDATE relates SET direction=?, description=?, created_at=? "
            "WHERE source_id=? AND target_id=?",
            (direction, description, datetime.now().isoformat(), id1, id2)
        )

    # 양방향이면 역방향도 기록
    if direction == "bidirectional":
        try:
            conn.execute(
                "INSERT OR REPLACE INTO relates (source_id, target_id, direction, description, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (id2, id1, "bidirectional", description, datetime.now().isoformat())
            )
        except Exception as e:
            _log.debug("reverse relate failed: %s", e)

    # 기존 metadata의 related_to도 유지 (호환성)
    for eid, other in [(id1,id2),(id2,id1)]:
        row = conn.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
        m = json.loads(row["metadata"]) if row["metadata"] else {}
        rel = m.get("related_to", [])
        if other not in rel: rel.append(other)
        m["related_to"] = rel
        conn.execute("UPDATE entities SET metadata=?,updated_at=? WHERE id=?",
            (json.dumps(m, ensure_ascii=False), datetime.now().isoformat(), eid))
        fp = T9/row["filepath"]
        if fp.exists() and fp.suffix == ".md":
            fm, body = parse_md(fp); fm["related_to"] = rel
            self_check("relate", fm); write_md(fp, fm, body)

    conn.commit(); conn.close()
    arrow = "\u2192" if direction == "source_to_target" else "\u2194"
    desc_str = f" ({description})" if description else ""
    print(f"  연결: [{id1}] {arrow} [{id2}]{desc_str}\n")


def cmd_digest_index(get_db, fhash, _upsert, _preview_len):
    """다이제스트 파일들을 FTS에 인덱싱"""
    conn = get_db()
    digest_dirs = [
        HANBEEN / "_legacy" / "_notion_dump" / "digested_final",
        HANBEEN / "_legacy" / "_personal_dump" / "digested_final",
    ]
    count = 0
    for ddir in digest_dirs:
        if not ddir.exists():
            print(f"  [SKIP] {ddir} 없음")
            continue
        src_label = str(ddir.parent.name)
        for f in sorted(ddir.glob("*.txt")):
            body = f.read_text(encoding="utf-8", errors="replace")
            rel = f"digest/{f.name}"
            if _upsert(conn, rel, f.name, "stabilized",
                       json.dumps({"source": "digest", "type": src_label}, ensure_ascii=False),
                       body[:_preview_len(f, body)], fhash(f), full_body=body):
                count += 1
        print(f"  [{src_label}] 스캔 완료")
    conn.commit(); conn.close()
    print(f"  다이제스트 {count}건 인덱싱 완료")


def cmd_legacy(query):
    if not LEGACY_DB.exists(): print(f"  레거시 DB 없음"); return
    conn = sqlite3.connect(str(LEGACY_DB)); conn.row_factory = sqlite3.Row
    rs = conn.execute("SELECT id,path,name,ext,dir,content_summary,ai_tags FROM files WHERE name LIKE ? OR path LIKE ? OR content_summary LIKE ? OR ai_tags LIKE ? ORDER BY modified DESC LIMIT 20",
        (f"%{query}%",)*4).fetchall()
    if not rs: print(f"  레거시 결과 없음: '{query}'")
    else:
        print(f"\n  === 레거시: '{query}' ({len(rs)}건) ===\n")
        for r in rs:
            print(f"  [{r['id']:4d}] {r['name'][:40]:40s} | {r['dir'] or '-'}")
            s = (r["content_summary"] or "")[:60].replace("\n"," ")
            if s: print(f"         {s}")
    conn.close(); print()


def cmd_ingest(cmd_capture, filepath):
    """카톡/메모 원본 파일을 파싱해서 핵심 아이디어를 개별 전개체로 등록."""
    import shutil
    fp = Path(filepath)
    if not fp.exists():
        print(f'  파일 없음: {filepath}'); return
    # 1. 원본을 inbox로 복사
    dest = FIELD / fp.name
    if not dest.exists():
        shutil.copy2(str(fp), str(dest))
        print(f'  원본 저장: {dest.name}')
    # 2. 파싱 — [이름] [시간] 메시지 형식
    text = fp.read_text(encoding='utf-8', errors='replace')
    messages = []
    for line in text.split(chr(10)):
        line = line.strip()
        if not line or line.startswith('---') or line == '\u3161': continue
        # [문 한빈] [시간] 내용 패턴
        if '] ' in line:
            parts = line.split('] ', 2)
            if len(parts) >= 3:
                msg = parts[-1].strip()
                if len(msg) > 15 and not msg.startswith('사진'):
                    messages.append(msg)
            elif len(parts) == 2:
                msg = parts[-1].strip()
                if len(msg) > 15 and not msg.startswith('사진'):
                    messages.append(msg)
    # 3. 의미 있는 메시지만 전개체 등록
    count = 0
    for msg in messages:
        if len(msg) > 20:  # 너무 짧은 건 스킵
            cmd_capture(msg)
            count += 1
    print(f'  {count}건 전개체 등록 완료 (원본 {len(messages)}건 중)')


def cmd_resurface(get_db, keyword=""):
    """침전(sediment) 상태 엔티티를 발굴. 키워드 없으면 랜덤 3~5개, 있으면 키워드 검색."""
    import random
    conn = get_db()
    if keyword:
        results = conn.execute(
            "SELECT id,filename,body_preview,concepts,updated_at FROM entities "
            "WHERE phase='sediment' AND (filename LIKE ? OR body_preview LIKE ? OR metadata LIKE ?) "
            "ORDER BY updated_at DESC LIMIT 10",
            (f"%{keyword}%",)*3).fetchall()
    else:
        all_sed = conn.execute(
            "SELECT id,filename,body_preview,concepts,updated_at FROM entities "
            "WHERE phase='sediment'").fetchall()
        count = min(max(3, len(all_sed)), 5) if all_sed else 0
        results = random.sample(list(all_sed), count) if count else []
    if not results:
        print("  침전 엔티티 없음." + (f" (키워드: {keyword})" if keyword else ""))
        conn.close(); return
    print(f"\n  === 침전 발굴 (resurface) ===" + (f" 키워드: {keyword}" if keyword else " 랜덤") + f" ({len(results)}건)\n")
    for r in results:
        preview = (r["body_preview"] or "")[:80].replace("\n", " ")
        tags = ""
        if r["concepts"]:
            try: tags = ", ".join(json.loads(r["concepts"]))
            except Exception: pass
        print(f"  [{r['id']:3d}] {r['filename'][:50]}")
        if preview: print(f"         {preview}")
        if tags: print(f"         개념: {tags}")
        print(f"         최종: {(r['updated_at'] or '')[:10]}")
        print()
    print("  발굴하려면: python3 t9_seed.py transition <id> reactivated\n")
    conn.close()


def cmd_rebuild_fts(get_db):
    """FTS5 인덱스를 완전 재구축. 검색 결과 누락 시 사용."""
    conn = get_db()
    print("  FTS5 인덱스 재구축 시작...")
    try:
        conn.execute("DROP TABLE IF EXISTS entities_fts")
        conn.execute("CREATE VIRTUAL TABLE entities_fts USING fts5(filename, body_preview, metadata_text)")
    except Exception as e:
        print(f"  [ERROR] FTS5 테이블 재생성 실패: {e}")
        conn.close(); return
    rows = conn.execute("SELECT id, filename, body_preview, metadata FROM entities").fetchall()
    count = 0
    for r in rows:
        try:
            conn.execute(
                "INSERT INTO entities_fts(rowid, filename, body_preview, metadata_text) VALUES(?,?,?,?)",
                (r["id"], r["filename"], r["body_preview"] or "", r["metadata"] or ""))
            count += 1
        except Exception as e:
            _log.debug("FTS rebuild skip [%d] %s: %s", r["id"], r["filename"], e)
    conn.commit(); conn.close()
    print(f"  FTS5 재구축 완료: {count}/{len(rows)}건 인덱싱")


def cmd_rebuild_vectors(get_db):
    """전체 엔티티 벡터 임베딩 재구축 (gemini-embedding-001)."""
    import time as _time
    try:
        from lib.vec import vec_available, batch_embeddings, upsert_vector, build_embed_text
    except ImportError:
        print("  [ERROR] lib/vec.py 또는 sqlite-vec 미설치")
        return

    conn = get_db()
    if not vec_available(conn):
        print("  [ERROR] sqlite-vec 사용 불가 (pip install sqlite-vec)")
        conn.close(); return

    rows = conn.execute(
        "SELECT id, filename, body_preview, concepts, phase FROM entities "
        "WHERE body_preview IS NOT NULL AND body_preview != '' ORDER BY id"
    ).fetchall()

    existing = set()
    try:
        existing = {r[0] for r in conn.execute("SELECT entity_id FROM entity_vectors").fetchall()}
    except Exception:
        pass

    todo = [r for r in rows if r["id"] not in existing]
    print(f"  벡터 임베딩: 전체 {len(rows)}건, 기존 {len(existing)}건 스킵, 신규 {len(todo)}건")

    if not todo:
        print("  신규 임베딩 대상 없음")
        conn.close(); return

    success, fail = 0, 0
    for i in range(0, len(todo), 100):
        chunk = todo[i:i+100]
        texts = [build_embed_text(r["body_preview"] or r["filename"],
                                  r["concepts"] or "", r["phase"] or "")
                 for r in chunk]
        embeddings = batch_embeddings(texts)

        for r, emb in zip(chunk, embeddings):
            if emb:
                upsert_vector(conn, r["id"], emb)
                success += 1
            else:
                fail += 1

        conn.commit()
        print(f"  진행: {min(i+100, len(todo))}/{len(todo)} (성공 {success}, 실패 {fail})")

        if i + 100 < len(todo):
            _time.sleep(0.5)

    conn.close()
    print(f"  벡터 재구축 완료: 성공 {success}, 실패 {fail}, 기존 {len(existing)}")


def cmd_orphans(get_db, fix=None):
    """파일이 사라진 고아 엔티티를 찾아 보고. --fix 옵션으로 sediment 전이.

    fix=None: sys.argv에서 --fix 여부 자동 감지 (CLI 직접 호출 시)
    fix=True/False: 호출자가 명시 (overnight.py, API 호출 시)
    """
    if fix is None:
        fix = "--fix" in sys.argv
    conn = get_db()
    rows = conn.execute("SELECT id, filepath, filename, phase FROM entities WHERE filepath IS NOT NULL AND filepath != ''").fetchall()
    orphans, corrupted = [], []
    for r in rows:
        if not isinstance(r["filepath"], str):
            corrupted.append(r)
            continue
        fp = T9 / r["filepath"]
        if not fp.exists():
            # HANBEEN 기준으로도 시도
            fp2 = HANBEEN / r["filepath"]
            if not fp2.exists():
                orphans.append(r)
    if corrupted:
        print(f"\n  === DB 오염 {len(corrupted)}건 (filepath가 정수) ===")
        for r in corrupted:
            print(f"  [{r['id']:4d}] filepath={repr(r['filepath'])}")
        if fix:
            for r in corrupted:
                conn.execute("DELETE FROM entities WHERE id=?", (r["id"],))
            conn.commit()
            print(f"  {len(corrupted)}건 삭제 완료")
    if not orphans:
        print("  고아 엔티티 없음 (모든 파일 존재 확인)")
    else:
        print(f"\n  === 고아 엔티티 {len(orphans)}건 (파일 없음) ===\n")
        for r in orphans:
            print(f"  [{r['id']:4d}] {r['phase']:15s} | {r['filename'][:50]}")
            print(f"         경로: {r['filepath']}")
        if fix:
            for r in orphans:
                conn.execute("UPDATE entities SET phase='sediment', updated_at=? WHERE id=?",
                    (datetime.now().isoformat(), r["id"]))
                conn.execute("INSERT INTO transitions (entity_id,from_phase,to_phase,timestamp,reason) VALUES(?,?,?,?,?)",
                    (r["id"], r["phase"], "sediment", datetime.now().isoformat(), "orphan: file missing"))
            conn.commit()
            print(f"\n  {len(orphans)}건 → sediment 전이 완료")
        else:
            print(f"\n  --fix 옵션으로 sediment 전이 가능: python3 t9_seed.py orphans --fix")
    conn.close()
