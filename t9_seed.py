#!/usr/bin/env python3
"""
T9 OS Seed v0.2 -- Simondonian Engine (리팩터링)
"The starting point is not Task but Tension."
NO "project" field. NO hardcoded classification.

v0.2: DB 보강, disparation, transduction, 동적 compose, digest 인덱싱
"""
import sys, os, re, sqlite3, json, time, hashlib, shutil
from datetime import datetime, timedelta
from pathlib import Path
from lib.parsers import parse_file, parse_md, write_md
from lib.ipc import cli as ipc_cli
from lib.export import cmd_export_json
from lib.commands import cmd_daily as _cmd_daily, cmd_tidy as _cmd_tidy
from lib.commands import cmd_compose as _cmd_compose, cmd_approve as _cmd_approve
from lib.transduction import find_transductions, format_transduction_report
from pipes.session_lock import cli_main as session_lock_cli

T9 = Path(__file__).resolve().parent
WORKSPACE = T9.parent
FIELD, ACTIVE = T9/"field"/"inbox", T9/"spaces"/"active"
SUSPENDED, ARCHIVED, MEMORY = T9/"spaces"/"suspended", T9/"spaces"/"archived", T9/"memory"
SEDIMENT = T9/"spaces"/"sediment"  # 침전: 삭제 아닌 가라앉음. 검색 가능, daily 제외
DB_PATH, LEGACY_DB = T9/".t9.db", T9/".t9_legacy.db"

# 마감일 파일: 여러 경로 fallback
DEADLINE_CANDIDATES = [
    WORKSPACE/"_notion_dump"/"T9_마감일.txt",
    WORKSPACE/"_legacy"/"_notion_dump"/"T9_마감일.txt",
    T9/"data"/"notion_dump"/"T9_마감일.txt",
    T9/"data"/"_notion_dump"/"T9_마감일.txt",
]

LOGS_DIR, LEARNED_PATH = T9/"logs", T9/"telos"/"LEARNED.md"
ARTIFACTS = T9/"artifacts"
IMPULSES = T9/"field"/"impulses"
CONVERSATIONS = T9/"data"/"conversations"
SESSION_BRIEFS = WORKSPACE/".claude"/"session-briefs"

DECISIONS = T9/"decisions"
COMPOSES = T9/"data"/"composes"
PROJECTS = WORKSPACE/"PROJECTS"

SCAN_DIRS = [FIELD, ACTIVE, SUSPENDED, ARCHIVED, SEDIMENT, MEMORY, ARTIFACTS,
             IMPULSES, T9/"field"/"scraps", T9/"telos", T9/"constitution",
             CONVERSATIONS, SESSION_BRIEFS, DECISIONS, COMPOSES]
# PROJECTS는 session-start 전체 reindex에서만 (2561파일, 심장박동에는 무거움)
SCAN_DIRS_HEAVY = [PROJECTS]  # 전체 reindex에서만 스캔
SCAN_DIRS_LIGHT = []  # 현재 미사용
SCAN_EXTS = {".md", ".docx", ".xlsx", ".pdf", ".hwp", ".txt", ".csv", ".log",
             ".zip", ".jpg", ".jpeg", ".png", ".mp4", ".svg"}

# 시몽동 위상 → 디렉토리 매핑 (impulse 추가)
PHASE_DIR = {
    "preindividual": FIELD, "impulse": IMPULSES,
    "tension_detected": FIELD, "candidate_generated": FIELD,
    "individuating": ACTIVE, "stabilized": ACTIVE, "split": ACTIVE,
    "merged": ACTIVE, "reactivated": ACTIVE,
    "suspended": SUSPENDED, "archived": ARCHIVED, "dissolved": ARCHIVED,
    "sediment": SEDIMENT,  # 침전: 지층으로 가라앉은 전개체
}

# body_preview 길이: 내용에 맞게 적응적으로 결정
def _preview_len(filepath, body=None):
    """
    파일의 성격과 내용 밀도에 따라 body_preview 길이를 적응적으로 결정.
    - 세션 대화: 가장 순수한 전개체 → 충분히 담아야 함
    - 짧은 파일: 전문 그대로
    - 긴 파일이지만 정보 밀도 높음(결정문, 브리프): 넉넉히
    - 긴 파일이지만 반복 많음(로그, CSV): 짧게
    """
    if body is None:
        body = ""
    total = len(body)

    # 짧은 파일은 전문 그대로 (잘라서 손실할 이유 없음)
    if total <= 1000:
        return total

    s = str(filepath)

    # 세션 대화 = 가장 순수한 전개체. 설계자의 날것 사유.
    if 'conversations' in s:
        # 대화 길이에 비례하되 상한 5000자
        return min(total, max(3000, total // 3))

    # 브리프/결정문 = 정보 밀도 높음. 전문에 가깝게.
    if any(k in s for k in ['session-briefs', 'brief', 'decisions', 'WORKING', 'BIBLE']):
        return min(total, 3000)

    # 구조화된 문서 (constitution, telos) = 핵심 앞부분에 집중
    if any(k in s for k in ['constitution', 'telos', 'artifacts']):
        return min(total, 2000)

    # 데이터 파일 (CSV, 로그) = 앞부분만
    if any(s.endswith(ext) for ext in ['.csv', '.log', '.txt']):
        return min(total, 500)

    # 기본: 파일 길이의 절반, 최소 500 최대 2000
    return min(total, max(500, total // 2))

# 상태 전이 그래프 (보강: split/merged/reactivated 경로)
TRANSITIONS = {
    "preindividual":       {"tension_detected", "impulse", "sediment"},
    "impulse":             {"tension_detected", "preindividual", "sediment"},
    "tension_detected":    {"candidate_generated", "suspended", "sediment"},
    "candidate_generated": {"individuating", "suspended", "sediment"},
    "individuating":       {"stabilized", "split", "merged", "suspended"},
    "stabilized":          {"archived", "split", "merged", "suspended", "reactivated"},
    "split":               {"preindividual", "tension_detected", "individuating", "suspended"},
    "merged":              {"preindividual", "tension_detected", "individuating", "suspended"},
    "suspended":           {"reactivated", "archived", "sediment"},
    "archived":            {"reactivated"},
    "reactivated":         {"tension_detected"},
    "sediment":            {"reactivated"},  # 침전에서도 발굴(reactivate) 가능
    "dissolved":           {"sediment"},     # 기존 dissolved도 sediment로 전이 가능
}

CONCEPT_KW = {
    "create":  ["만들","구현","개발","build","create","코딩","작성","생성"],
    "explore": ["조사","탐색","리서치","explore","research","분석"],
    "solve":   ["해결","수정","fix","solve","버그","오류","debug"],
    "earn":    ["수익","돈","earn","매출","사업"],
    "express": ["발표","쓰기","express","글","에세이"],
    "become":  ["공부","배우","become","성장","학습"],
}
URGENCY_KW = {"high":["급","긴급","urgent","asap","마감","오늘","당장"], "low":["나중","천천히","여유","someday"]}

USAGE = """  사용법: python3 t9_seed.py <command> [args]
  capture/idea <text>   전개체 저장
  reindex               파일 → DB 동기화
  search <query>        검색
  status                전체 현황
  daily                 일일 브리프
  transition <id> <phase> [reason]
  compose/do <text>     플랜 생성
  approve <id> <plan>   플랜 승인
  reflect               주간 반성
  consolidate           아카이브 → 메모리 통합
  history <id>          전이 이력
  relate <id1> <id2>    엔티티 연결
  legacy <query>        레거시 DB 검색
  ipc <cmd>             세션 간 통신
  claim <project> [desc] 프로젝트 claim
  claim-file <path>     파일 claim
  sessions              활성 세션 목록
  release [project]     claim 해제
  check <path>          파일 충돌 확인
  done <id>             → stabilized
  go <id>               → individuating
  resurface [keyword]   침전(sediment) 엔티티 발굴 (랜덤 3~5개 또는 키워드 검색)
  tidy                  주기 정리 (일/수 자동: inbox→active/archived)"""

# ─── 파일 파싱 ───────────────────────────────────────────────────────────────

# ─── DB ──────────────────────────────────────────────────────────────────────

# 보강된 정규 컬럼 목록 (마이그레이션 대상)
_EXTRA_COLUMNS = {
    "created_at": "TEXT",      # preindividual 진입 시각
    "parent_id":  "INTEGER",   # split/merged 관계 추적
    "urgency":    "TEXT",      # high/mid/low (정규 컬럼)
    "concepts":   "TEXT",      # JSON array (정규 컬럼)
}

def _migrate_db(conn):
    """기존 DB에 누락된 컬럼이 있으면 ALTER TABLE로 추가. DROP TABLE 절대 금지."""
    existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(entities)").fetchall()}
    for col, ctype in _EXTRA_COLUMNS.items():
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE entities ADD COLUMN {col} {ctype}")
    # relates 테이블 (transduction 기록용)
    conn.execute("""CREATE TABLE IF NOT EXISTS relates (
        id INTEGER PRIMARY KEY,
        source_id INTEGER NOT NULL,
        target_id INTEGER NOT NULL,
        direction TEXT DEFAULT 'bidirectional',
        description TEXT,
        created_at TEXT,
        UNIQUE(source_id, target_id)
    )""")
    # relates 테이블에 direction 컬럼이 없으면 추가
    rel_cols = {r[1] for r in conn.execute("PRAGMA table_info(relates)").fetchall()}
    if "direction" not in rel_cols:
        try: conn.execute("ALTER TABLE relates ADD COLUMN direction TEXT DEFAULT 'bidirectional'")
        except Exception: pass
    if "description" not in rel_cols:
        try: conn.execute("ALTER TABLE relates ADD COLUMN description TEXT")
        except Exception: pass
    conn.commit()

def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("""CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY, filepath TEXT UNIQUE, filename TEXT,
        phase TEXT DEFAULT 'preindividual', metadata JSON,
        body_preview TEXT, file_hash TEXT, updated_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS transitions (
        id INTEGER PRIMARY KEY, entity_id INTEGER, from_phase TEXT,
        to_phase TEXT, timestamp TEXT, reason TEXT)""")
    try: conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(filename, body_preview, metadata_text)")
    except Exception: pass
    # 마이그레이션: 정규 컬럼 + relates 테이블
    _migrate_db(conn)
    return conn

# ─── 유틸 ────────────────────────────────────────────────────────────────────

def fhash(filepath):
    return hashlib.md5(Path(filepath).read_bytes()).hexdigest()[:12]

def self_check(op="write", meta=None):
    """스키마 위반 검사. 정규 컬럼은 허용 목록에 포함."""
    violations = []
    allowed = {"id","filepath","filename","phase","metadata","body_preview",
               "file_hash","updated_at","created_at","parent_id","urgency","concepts"}
    try:
        conn = get_db()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(entities)").fetchall()}
        extra = cols - allowed
        if extra: violations.append(f"SCHEMA_VIOLATION: extra columns {extra}")
        conn.close()
    except Exception: pass
    if violations:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOGS_DIR/f"self_check_{datetime.now():%Y%m%d}.log", "a") as f:
            for v in violations: f.write(f"[{datetime.now().isoformat()}] {op}: {v}\n")
        for v in violations: print(f"  [VIOLATION] {v}")
    return violations

def extract_concepts(text):
    tl = text.lower()
    return [c for c, kws in CONCEPT_KW.items() if any(k in tl for k in kws)]

def detect_urgency(text):
    tl = text.lower()
    for lv, kws in URGENCY_KW.items():
        if any(k in tl for k in kws): return lv
    return "mid"

def _detect_tension(text):
    """텍스트에서 긴장(tension)을 감지. 대립하는 키워드쌍이 동시에 존재하면 True."""
    tl = text.lower()
    # 대립 차원: (dimension_a 키워드, dimension_b 키워드)
    oppositions = [
        (["빠르","급","asap","urgent","당장"], ["천천히","나중","여유","someday","장기"]),
        (["build","만들","구현","개발"], ["buy","구매","외주","서비스"]),
        (["단순","최소","간단"], ["복잡","완벽","정교"]),
        (["혼자","단독"], ["협업","팀","같이"]),
    ]
    dim_labels = [
        ("urgency_high", "urgency_low"),
        ("build", "buy"),
        ("simplicity", "complexity"),
        ("solo", "collaboration"),
    ]
    for (kws_a, kws_b), (label_a, label_b) in zip(oppositions, dim_labels):
        has_a = any(k in tl for k in kws_a)
        has_b = any(k in tl for k in kws_b)
        if has_a and has_b:
            return True, label_a, label_b
    return False, "", ""

def _find_deadline_file():
    """마감일 파일을 여러 후보 경로에서 찾음. 없으면 None 반환 (빈 파일 생성 금지)."""
    for candidate in DEADLINE_CANDIDATES:
        if candidate.exists():
            return candidate
        # 심볼릭 링크가 깨졌을 수 있으므로 is_symlink도 체크
        if candidate.is_symlink():
            continue
    return None

# ─── DB 업서트 ───────────────────────────────────────────────────────────────

def _upsert(conn, rel, fname, phase, meta_json, preview, h, full_body="",
            created_at=None, parent_id=None, urgency=None, concepts=None):
    now = datetime.now().isoformat()
    row = conn.execute("SELECT id, file_hash FROM entities WHERE filepath=?", (rel,)).fetchone()
    if row and row["file_hash"] == h: return False

    # concepts를 JSON array 문자열로 변환
    concepts_str = json.dumps(concepts, ensure_ascii=False) if concepts else None

    if row:
        conn.execute("""UPDATE entities SET phase=?,metadata=?,body_preview=?,file_hash=?,
            updated_at=?,filename=?,urgency=?,concepts=? WHERE filepath=?""",
            (phase, meta_json, preview, h, now, fname, urgency, concepts_str, rel))
        eid = row["id"]
    else:
        conn.execute("""INSERT INTO entities (filepath,filename,phase,metadata,body_preview,
            file_hash,updated_at,created_at,parent_id,urgency,concepts) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (rel, fname, phase, meta_json, preview, h, now,
             created_at or now, parent_id, urgency, concepts_str))
        eid = conn.execute("SELECT id FROM entities WHERE filepath=?", (rel,)).fetchone()["id"]
    try:
        conn.execute("DELETE FROM entities_fts WHERE rowid=?", (eid,))
        conn.execute("INSERT INTO entities_fts(rowid,filename,body_preview,metadata_text) VALUES(?,?,?,?)",
            (eid, fname, full_body or preview, meta_json))
    except Exception: pass
    return True

def _index_file(filepath):
    conn = get_db()
    rel = str(filepath.relative_to(T9))
    meta, body = parse_file(filepath)
    concepts = extract_concepts(body) if body else []
    urgency = detect_urgency(body) if body else "mid"
    if not meta.get("concepts") and concepts:
        meta["concepts"] = concepts
    if not meta.get("urgency") and urgency != "mid":
        meta["urgency"] = urgency
    _upsert(conn, rel, filepath.name, meta.get("phase","preindividual"),
            json.dumps(meta, ensure_ascii=False), body[:_preview_len(filepath, body)], fhash(filepath),
            full_body=body, urgency=urgency or "mid",
            concepts=concepts, parent_id=meta.get("parent_id"))
    conn.commit(); conn.close()

# ─── 명령어 ──────────────────────────────────────────────────────────────────

def cmd_capture(text):
    """전개체 저장. tension 감지 시 disparation 메타데이터 기록."""
    now = datetime.now()
    title = re.sub(r'[^\w\s가-힣]', '', text[:30]).strip() or f"tension_{now:%H%M%S}"
    filepath = FIELD / f"{now:%Y%m%d}_{title}_{now:%H%M%S}.md"
    FIELD.mkdir(parents=True, exist_ok=True)
    concepts, urgency = extract_concepts(text), detect_urgency(text)

    meta = {
        "phase": "preindividual",
        "created": f"{now:%Y-%m-%d %H:%M}",
        "concepts": concepts,
        "urgency": urgency,
    }

    # 긴장(tension) 감지 → disparation 기록
    has_tension, dim_a, dim_b = _detect_tension(text)
    if has_tension:
        meta["disparation"] = {
            "dimension_a": dim_a,
            "dimension_b": dim_b,
            "resolution": "",  # 해소 시 수동으로 기록
        }
        meta["phase"] = "tension_detected"
        print(f"  [!] 긴장 감지: {dim_a} vs {dim_b}")

    write_md(filepath, meta, text)
    self_check("capture", meta)
    print(f"  저장: {filepath.name}")
    if concepts: print(f"  개념: {', '.join(concepts)}")

    # 전도(transduction) 자동 탐지: _index_file 전에 실행하여 self-match 방지
    try:
        conn = get_db()
        transductions = find_transductions(conn, concepts, text)
        report = format_transduction_report(transductions)
        if report:
            print(report)
    except Exception as e:
        print(f"  [warn] 전도 탐지 실패: {e}", file=__import__('sys').stderr)

    _index_file(filepath)

def cmd_reindex(incremental=False):
    conn = get_db()
    existing = {r["filepath"]: r["file_hash"] for r in conn.execute("SELECT filepath, file_hash FROM entities").fetchall()}
    found, count, skipped = set(), 0, 0
    # 전체 디렉토리 + T9 루트 스캔
    sources = [(sd, True, SCAN_EXTS) for sd in SCAN_DIRS] + [(T9, False, SCAN_EXTS)]
    # 경량 스캔 (MD만)
    for ld in SCAN_DIRS_LIGHT:
        sources.append((ld, True, {".md", ".txt"}))
    # 무거운 디렉토리: 전체 reindex에서만 (incremental 아닐 때)
    if not incremental:
        for hd in SCAN_DIRS_HEAVY:
            sources.append((hd, True, {".md", ".txt"}))
    for src, recurse, exts in sources:
        if not src.exists(): continue
        files = []
        for ext in exts:
            files.extend(src.rglob(f"*{ext}") if recurse else src.glob(f"*{ext}"))
        SKIP_DIRS = {'node_modules', '.next', '__pycache__', '.git', 'venv', '.venv', 'dist', 'build'}
        for f in files:
            if f.name.startswith("."): continue
            if any(skip in f.parts for skip in SKIP_DIRS): continue
            try:
                rel = str(f.relative_to(T9)) if recurse else f.name
            except ValueError:
                try:
                    rel = str(f.relative_to(WORKSPACE))
                except ValueError:
                    rel = f.name
            found.add(rel)
            # 증분 모드: hash 동일하면 스킵 (파싱 절약)
            if incremental and rel in existing:
                current_hash = fhash(f)
                if current_hash == existing[rel]:
                    skipped += 1
                    continue
            meta, body = parse_file(f)
            concepts = extract_concepts(body) if body else []
            urgency = detect_urgency(body) if body else "mid"
            if not meta.get("concepts") and concepts:
                meta["concepts"] = concepts
            if not meta.get("urgency") and urgency != "mid":
                meta["urgency"] = urgency
            if _upsert(conn, rel, f.name, meta.get("phase","preindividual"),
                       json.dumps(meta, ensure_ascii=False), body[:_preview_len(f, body)], fhash(f),
                       full_body=body, urgency=urgency or "mid",
                       concepts=concepts, parent_id=meta.get("parent_id")):
                count += 1
    for d in set(existing.keys()) - found:
        conn.execute("DELETE FROM entities WHERE filepath=?", (d,)); count += 1
    conn.commit(); conn.close()
    self_check("reindex")
    print(f"  스캔: {len(found)}건, 갱신: {count}건")

def cmd_search(query):
    conn = get_db()
    try:
        safe_query = '"' + query.replace('"', '') + '"'
        results = conn.execute(
            "SELECT e.id,e.filename,e.phase,e.metadata,e.urgency,e.concepts "
            "FROM entities_fts f JOIN entities e ON f.rowid=e.id "
            "WHERE entities_fts MATCH ? LIMIT 20", (safe_query,)).fetchall()
    except Exception:
        results = []
    if not results:
        results = conn.execute(
            "SELECT id,filename,phase,metadata,urgency,concepts FROM entities "
            "WHERE filename LIKE ? OR body_preview LIKE ? OR metadata LIKE ? LIMIT 20",
            (f"%{query}%",)*3).fetchall()
    if not results: print("  결과 없음")
    else:
        for r in results:
            # 정규 컬럼 우선, fallback으로 metadata
            tags = r["concepts"] or ""
            if tags:
                try: tags = ", ".join(json.loads(tags))
                except Exception: pass
            else:
                m = json.loads(r["metadata"]) if r["metadata"] else {}
                tags = m.get("concepts", m.get("tags",""))
                if isinstance(tags, list): tags = ", ".join(str(t) for t in tags)
            urg = r["urgency"] or ""
            urg_mark = f" [{urg}]" if urg and urg != "mid" else ""
            print(f"  [{r['id']:3d}] {r['phase'][:12]:12s} | {r['filename'][:50]:50s} | {tags}{urg_mark}")
    conn.close()

def cmd_status():
    conn = get_db()
    phases = conn.execute("SELECT phase, COUNT(*) as cnt FROM entities GROUP BY phase ORDER BY cnt DESC").fetchall()
    total = sum(r["cnt"] for r in phases)
    print(f"\n  === T9 OS Seed v0.2 (총 {total}건) ===\n")
    for r in phases:
        print(f"  {r['phase']:20s} {r['cnt']:4d}  {'#'*min(r['cnt'],30)}")
    # 관계(relates) 수
    rel_count = conn.execute("SELECT COUNT(*) as c FROM relates").fetchone()["c"]
    if rel_count:
        print(f"\n  관계(transduction): {rel_count}건")
    conn.close()

def _is_movable(filepath_rel):
    """파일이 이동 가능한지 판단. PHASE_DIR에 매핑된 폴더 안의 파일만 이동 가능.
    constitution/, telos/ 등 구조적 폴더의 파일은 그 자리에 있는 것이 존재 의미."""
    movable_roots = {str(d.relative_to(T9)).split("/")[0] for d in PHASE_DIR.values() if d != T9}
    # field, spaces, artifacts, memory 등만 이동 대상
    first_part = Path(filepath_rel).parts[0] if Path(filepath_rel).parts else ""
    return first_part in movable_roots

def cmd_transition(eid, to_phase, reason=""):
    conn = get_db()
    row = conn.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
    if not row: print(f"  ID {eid} 없음"); conn.close(); return
    fp = row["phase"]
    if to_phase not in TRANSITIONS.get(fp, set()):
        print(f"  전이 불가: {fp} -> {to_phase}  허용: {', '.join(TRANSITIONS.get(fp,set()))}"); conn.close(); return
    old_path = T9 / row["filepath"]
    is_protected = not _is_movable(row["filepath"])
    # 보호된 파일은 DB phase만 업데이트, 파일 이동 안 함
    if is_protected:
        meta = json.loads(row["metadata"]) if row["metadata"] else {}
        meta["phase"], meta["transitioned_at"] = to_phase, f"{datetime.now():%Y-%m-%d %H:%M}"
        if old_path.suffix == ".md" and old_path.exists():
            _, body = parse_md(old_path)
            write_md(old_path, meta, body)  # 제자리에 메타만 업데이트
        new_rel = row["filepath"]  # 경로 변경 없음
    elif old_path.suffix == ".md":
        meta, body = parse_md(old_path)
        meta["phase"], meta["transitioned_at"] = to_phase, f"{datetime.now():%Y-%m-%d %H:%M}"
        new_dir = PHASE_DIR.get(to_phase, FIELD); new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / old_path.name
        self_check("transition", meta); write_md(new_path, meta, body)
        if old_path != new_path and old_path.exists(): old_path.unlink()
        new_rel = str(new_path.relative_to(T9))
    else:
        meta = json.loads(row["metadata"]) if row["metadata"] else {}
        meta["phase"], meta["transitioned_at"] = to_phase, f"{datetime.now():%Y-%m-%d %H:%M}"
        new_dir = PHASE_DIR.get(to_phase, FIELD); new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / old_path.name
        if old_path != new_path and old_path.exists():
            try:
                shutil.move(str(old_path), str(new_path))
            except PermissionError:
                # WSL→NTFS 크로스 파일시스템: copy+delete fallback
                shutil.copy2(str(old_path), str(new_path))
                try:
                    old_path.unlink()
                except PermissionError:
                    pass  # 원본 삭제 실패해도 DB는 새 경로로 업데이트
        new_rel = str(new_path.relative_to(T9))
    conn.execute("UPDATE entities SET phase=?,filepath=?,updated_at=?,metadata=? WHERE id=?",
        (to_phase, new_rel, datetime.now().isoformat(), json.dumps(meta, ensure_ascii=False), eid))
    conn.execute("INSERT INTO transitions (entity_id,from_phase,to_phase,timestamp,reason) VALUES(?,?,?,?,?)",
        (eid, fp, to_phase, datetime.now().isoformat(), reason))
    conn.commit(); conn.close()
    print(f"  {fp} -> {to_phase}: {old_path.name}")

def cmd_tidy():
    _cmd_tidy(get_db, cmd_transition)


def cmd_daily():
    _cmd_daily(get_db, _find_deadline_file)

def _parse_deadlines():
    from lib.commands import _parse_deadlines as _pd
    return _pd(_find_deadline_file)

def cmd_compose(text):
    _cmd_compose(text, extract_concepts, detect_urgency, _detect_tension)


def cmd_approve(cid, choice):
    _cmd_approve(cid, choice, self_check, write_md, _index_file)


def cmd_reflect():
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

def cmd_consolidate():
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
            except Exception: pass
    conn.commit(); conn.close()
    print(f"\n  총 {total}건 통합.\n")

def cmd_watch(interval=5):
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

def cmd_history(eid):
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
            arrow = "→" if r["direction"] == "source_to_target" else "↔"
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

def cmd_relate(id1, id2, direction="bidirectional", description=""):
    """엔티티 연결. transduction 기록 (방향성 지원).

    direction: "bidirectional" | "source_to_target" (id1→id2)
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
        except Exception: pass

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
    arrow = "→" if direction == "source_to_target" else "↔"
    desc_str = f" ({description})" if description else ""
    print(f"  연결: [{id1}] {arrow} [{id2}]{desc_str}\n")

def cmd_digest_index():
    """다이제스트 파일들을 FTS에 인덱싱"""
    conn = get_db()
    digest_dirs = [
        WORKSPACE / "_legacy" / "_notion_dump" / "digested_final",
        WORKSPACE / "_legacy" / "_personal_dump" / "digested_final",
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

def cmd_ingest(filepath):
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
        if not line or line.startswith('---') or line == 'ㅡ': continue
        # [이름] [시간] 내용 패턴
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

def cmd_resurface(keyword=""):
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

def main():
    if len(sys.argv) < 2: print(USAGE); return
    c = sys.argv[1]
    if c=="capture" and len(sys.argv)>2: cmd_capture(" ".join(sys.argv[2:]))
    elif c=="reindex": cmd_reindex(incremental="--incremental" in sys.argv or "-i" in sys.argv)
    elif c=="search" and len(sys.argv)>2: cmd_search(" ".join(sys.argv[2:]))
    elif c=="status": cmd_status()
    elif c=="daily": cmd_daily()
    elif c=="transition" and len(sys.argv)>=4:
        cmd_transition(int(sys.argv[2]), sys.argv[3], " ".join(sys.argv[4:]) if len(sys.argv)>4 else "")
    elif c=="compose" and len(sys.argv)>2: cmd_compose(" ".join(sys.argv[2:]))
    elif c=="approve" and len(sys.argv)>=4: cmd_approve(sys.argv[2], sys.argv[3])
    elif c=="reflect": cmd_reflect()
    elif c=="consolidate": cmd_consolidate()
    elif c=="watch": cmd_watch(int(sys.argv[2]) if len(sys.argv)>2 else 5)
    elif c=="history" and len(sys.argv)>=3: cmd_history(int(sys.argv[2]))
    elif c=="relate" and len(sys.argv)>=4:
        direction = sys.argv[4] if len(sys.argv)>4 else "bidirectional"
        description = " ".join(sys.argv[5:]) if len(sys.argv)>5 else ""
        cmd_relate(int(sys.argv[2]), int(sys.argv[3]), direction, description)
    elif c=="digest": cmd_digest_index()
    elif c=="ingest" and len(sys.argv)>2: cmd_ingest(" ".join(sys.argv[2:]))
    elif c=="legacy" and len(sys.argv)>2: cmd_legacy(" ".join(sys.argv[2:]))
    elif c=="export-json": cmd_export_json()
    elif c=="done" and len(sys.argv)>=3: cmd_transition(int(sys.argv[2]), "stabilized", " ".join(sys.argv[3:]) if len(sys.argv)>3 else "완료")
    elif c=="go" and len(sys.argv)>=3: cmd_transition(int(sys.argv[2]), "individuating", " ".join(sys.argv[3:]) if len(sys.argv)>3 else "시작")
    elif c=="resurface": cmd_resurface(" ".join(sys.argv[2:]) if len(sys.argv)>2 else "")
    elif c=="tidy": cmd_tidy()
    elif c=="do" and len(sys.argv)>2: cmd_compose(" ".join(sys.argv[2:]))
    elif c=="idea" and len(sys.argv)>2: cmd_capture(" ".join(sys.argv[2:]))
    elif c=="ipc": ipc_cli(sys.argv[2:])
    elif c in ("claim","claim-file","sessions","release","check-conflicts"):
        session_lock_cli([c] + sys.argv[2:])
    elif c=="check" and len(sys.argv)>=3:
        session_lock_cli(["check", sys.argv[2]])
    else: print(f"  알 수 없는 명령: {c}"); print(USAGE)

if __name__ == "__main__":
    main()
