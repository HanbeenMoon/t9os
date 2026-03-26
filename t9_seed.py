#!/usr/bin/env python3
"""
T9 OS Seed v0.2 -- Simondonian Engine (리팩터링)
"The starting point is not Task but Tension."
NO "project" field. NO hardcoded classification.

v0.2: DB 보강, disparation, transduction, 동적 compose, digest 인덱싱
"""
import sys, os, re, sqlite3, json, time, hashlib, shutil, logging
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    level=logging.WARNING,
)
_log = logging.getLogger("t9_seed")
from lib.parsers import parse_file, parse_md, write_md
from lib.ipc import cli as ipc_cli
from lib.export import cmd_export_json
from lib.commands import cmd_daily as _cmd_daily, cmd_tidy as _cmd_tidy
from lib.commands import cmd_compose as _cmd_compose, cmd_approve as _cmd_approve
from lib.transduction import find_transductions, format_transduction_report
from lib.config import DB_PATH  # WSL 네이티브 DB (NTFS 잠금 방지)
from pipes.session_lock import cli_main as session_lock_cli
from lib.commands_ext import (
    cmd_reflect as _cmd_reflect, cmd_consolidate as _cmd_consolidate,
    cmd_watch as _cmd_watch, cmd_history as _cmd_history,
    cmd_relate as _cmd_relate, cmd_digest_index as _cmd_digest_index,
    cmd_legacy as _cmd_legacy, cmd_ingest as _cmd_ingest,
    cmd_resurface as _cmd_resurface, cmd_rebuild_fts as _cmd_rebuild_fts,
    cmd_orphans as _cmd_orphans,
)

T9 = Path(__file__).resolve().parent
HANBEEN = T9.parent
FIELD, ACTIVE = T9/"field"/"inbox", T9/"spaces"/"active"
SUSPENDED, ARCHIVED, MEMORY = T9/"spaces"/"suspended", T9/"spaces"/"archived", T9/"memory"
SEDIMENT = T9/"spaces"/"sediment"  # 침전: 삭제 아닌 가라앉음. 검색 가능, daily 제외
LEGACY_DB = T9/".t9_legacy.db"

# 마감일: DB(entities.deadline_date)가 단일 소스.
# 레거시 Notion dump fallback은 유지하되, daily에서 DB 우선 사용.
DEADLINE_CANDIDATES = [
    T9/"data"/"notion_dump"/"T9_마감일.txt",       # 레거시 fallback (삭제 예정)
]

LOGS_DIR, LEARNED_PATH = T9/"logs", T9/"telos"/"LEARNED.md"
ARTIFACTS = T9/"artifacts"
IMPULSES = T9/"field"/"impulses"
CONVERSATIONS = T9/"data"/"conversations"
SESSION_BRIEFS = HANBEEN/".claude"/"session-briefs"

DECISIONS = T9/"decisions"
COMPOSES = T9/"data"/"composes"
PROJECTS = HANBEEN/"PROJECTS"

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

    # 세션 대화 = 가장 순수한 전개체. 한빈의 날것 사유.
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
# urgency는 키워드 추론하지 않음. 한빈이 직접 지정하거나 마감일 기반으로만 판단.
URGENCY_KW = {}

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
  tidy                  주기 정리 (일/수 자동: inbox→active/archived)
  rebuild-fts           FTS5 검색 인덱스 완전 재구축
  orphans [--fix]       고아 엔티티 탐지 (파일 없는 DB 레코드). --fix로 sediment 전이"""

# ─── 파일 파싱 ───────────────────────────────────────────────────────────────

# ─── DB ──────────────────────────────────────────────────────────────────────

# 보강된 정규 컬럼 목록 (마이그레이션 대상)
_EXTRA_COLUMNS = {
    "created_at": "TEXT",      # preindividual 진입 시각
    "parent_id":  "INTEGER",   # split/merged 관계 추적
    "urgency":    "TEXT",      # high/mid/low (정규 컬럼)
    "concepts":   "TEXT",      # JSON array (정규 컬럼)
    "deadline_date": "TEXT",   # ISO date (2026-04-04). 마감 있는 엔티티만 필터하면 일정 뷰.
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
        except Exception as e: _log.debug("relates.direction already exists: %s", e)
    if "description" not in rel_cols:
        try: conn.execute("ALTER TABLE relates ADD COLUMN description TEXT")
        except Exception as e: _log.debug("relates.description already exists: %s", e)
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
    except Exception as e: _log.debug("FTS5 table exists or unavailable: %s", e)
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
               "file_hash","updated_at","created_at","parent_id","urgency","concepts","deadline_date"}
    try:
        conn = get_db()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(entities)").fetchall()}
        extra = cols - allowed
        if extra: violations.append(f"SCHEMA_VIOLATION: extra columns {extra}")
        conn.close()
    except Exception as e:
        _log.warning("self_check DB access failed: %s", e)
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
    """urgency는 키워드 추론 안 함. 한빈이 직접 지정하거나 마감일 기반으로만."""
    return None

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
    except Exception as e:
        _log.debug("FTS upsert failed for %s: %s", fname, e)
    return True

def _build_entity_payload(filepath, meta, body):
    """파일에서 엔티티 페이로드를 구성하는 공통 로직."""
    concepts = extract_concepts(body) if body else []
    urgency = detect_urgency(body) if body else None
    if not meta.get("concepts") and concepts:
        meta["concepts"] = concepts
    if not meta.get("urgency") and urgency:
        meta["urgency"] = urgency
    return {
        "fname": filepath.name,
        "phase": meta.get("phase", "preindividual"),
        "meta_json": json.dumps(meta, ensure_ascii=False),
        "preview": body[:_preview_len(filepath, body)],
        "h": fhash(filepath),
        "full_body": body,
        "urgency": urgency,
        "concepts": concepts,
        "parent_id": meta.get("parent_id"),
    }

def _index_file(filepath):
    conn = get_db()
    rel = str(filepath.relative_to(T9))
    meta, body = parse_file(filepath)
    p = _build_entity_payload(filepath, meta, body)
    _upsert(conn, rel, p["fname"], p["phase"], p["meta_json"], p["preview"], p["h"],
            full_body=p["full_body"], urgency=p["urgency"],
            concepts=p["concepts"], parent_id=p["parent_id"])
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

    # 마감 날짜 자동 감지
    try:
        from lib.deadline_harvest import extract_date
        deadline = extract_date(text)
        if deadline:
            meta["deadline_date"] = deadline
            print(f"  [마감 감지] {deadline}")
    except Exception:
        deadline = None

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

    # deadline_date를 DB 컬럼에 직접 기록
    if deadline:
        try:
            conn = get_db()
            rel = str(filepath.relative_to(T9))
            conn.execute("UPDATE entities SET deadline_date=? WHERE filepath=?", (deadline, rel))
            conn.commit(); conn.close()
        except Exception:
            pass

    # 즉시 제목 정제 (Gemini Flash) — 6시간 대기 없이 capture 시점에 바로
    try:
        from pipes.t9_auto import gemini_call
        now_str = datetime.now().strftime("%Y-%m-%d")
        refine_prompt = (
            f'다음 텍스트에서 깔끔한 제목을 1줄로 추출해. 날짜가 있으면 YYYY-MM-DD로. '
            f'오늘은 {now_str}. JSON으로만 답해: {{"title":"제목","date":"YYYY-MM-DD 또는 null"}}\n\n'
            f'{text[:200]}'
        )
        raw = gemini_call(refine_prompt, max_tokens=80)
        if raw:
            import json as _json
            _m = re.search(r'\{.*\}', raw, re.DOTALL)
            if _m:
                parsed = _json.loads(_m.group())
                conn = get_db()
                rel = str(filepath.relative_to(T9))
                row = conn.execute("SELECT id, metadata FROM entities WHERE filepath=?", (rel,)).fetchone()
                if row:
                    try:
                        meta_db = _json.loads(row["metadata"]) if row["metadata"] else {}
                    except Exception:
                        meta_db = {}
                    if parsed.get("title"):
                        meta_db["display_title"] = parsed["title"]
                    if parsed.get("date") and parsed["date"] != "null" and re.match(r'\d{4}-\d{2}-\d{2}', str(parsed["date"])):
                        conn.execute("UPDATE entities SET deadline_date=? WHERE id=?", (parsed["date"], row["id"]))
                    conn.execute("UPDATE entities SET metadata=? WHERE id=?",
                                 (_json.dumps(meta_db, ensure_ascii=False), row["id"]))
                    conn.commit()
                    dt = parsed.get("title", "")
                    if dt:
                        print(f"  [정제] {dt}")
                conn.close()
    except Exception:
        pass  # Gemini 실패해도 capture는 정상 진행

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
                    rel = str(f.relative_to(HANBEEN))
                except ValueError:
                    rel = f.name
            found.add(rel)
            try:
                # 증분 모드: hash 동일하면 스킵 (파싱 절약)
                if incremental and rel in existing:
                    current_hash = fhash(f)
                    if current_hash == existing[rel]:
                        skipped += 1
                        continue
                meta, body = parse_file(f)
                p = _build_entity_payload(f, meta, body)
                if _upsert(conn, rel, p["fname"], p["phase"], p["meta_json"], p["preview"], p["h"],
                           full_body=p["full_body"], urgency=p["urgency"],
                           concepts=p["concepts"], parent_id=p["parent_id"]):
                    count += 1
            except (OSError, sqlite3.Error, ValueError, json.JSONDecodeError) as e:
                _log.warning("reindex skip %s: %s", f.name, e)
                continue
    # 스캔 범위 밖 데이터(digest 등)는 보호 — 삭제 대상에서 제외
    PROTECTED_PREFIXES = ("_legacy/", "memory/memory_")
    for d in set(existing.keys()) - found:
        if any(d.startswith(p) for p in PROTECTED_PREFIXES):
            continue  # 수동 등록 데이터 보호
        conn.execute("DELETE FROM entities WHERE filepath=?", (d,)); count += 1
    conn.commit()
    # 마감 수확: 3개 소스에서 deadline_date 통합
    try:
        from lib.deadline_harvest import harvest_deadlines
        dl_count = harvest_deadlines(conn)
        if dl_count > 0:
            print(f"  마감 수확: {dl_count}건")
    except Exception as e:
        _log.warning("deadline harvest failed: %s", e)
    conn.close()
    self_check("reindex")
    print(f"  스캔: {len(found)}건, 갱신: {count}건")

def cmd_search(query):
    conn = get_db()
    # LIKE 검색 (한글 완벽 지원, 최신+관련도 정렬)
    results = conn.execute(
        "SELECT id,filename,phase,metadata,urgency,concepts FROM entities "
        "WHERE filename LIKE ? OR body_preview LIKE ? OR concepts LIKE ? OR metadata LIKE ? "
        "ORDER BY "
        "  CASE WHEN filename LIKE ? THEN 0 ELSE 1 END, "  # 파일명 매치 우선
        "  CASE WHEN phase='stabilized' THEN 0 WHEN phase='tension_detected' THEN 1 ELSE 2 END, "
        "  id DESC "
        "LIMIT 40",
        (f"%{query}%",)*4 + (f"%{query}%",)).fetchall()
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
    _cmd_reflect(get_db)

def cmd_consolidate():
    _cmd_consolidate(get_db, fhash, _upsert, _preview_len)

def cmd_watch(interval=5):
    _cmd_watch(get_db, fhash, cmd_reindex, interval)

def cmd_history(eid):
    _cmd_history(get_db, eid)

def cmd_relate(id1, id2, direction="bidirectional", description=""):
    _cmd_relate(get_db, self_check, id1, id2, direction, description)

def cmd_digest_index():
    _cmd_digest_index(get_db, fhash, _upsert, _preview_len)

def cmd_legacy(query):
    _cmd_legacy(query)

def cmd_ingest(filepath):
    _cmd_ingest(cmd_capture, filepath)

def cmd_resurface(keyword=""):
    _cmd_resurface(get_db, keyword)

def cmd_rebuild_fts():
    _cmd_rebuild_fts(get_db)

def cmd_orphans():
    _cmd_orphans(get_db)

def cmd_deadlines(show_all=False):
    """마감 뷰 — deadline_date가 있는 엔티티만 필터."""
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    # 마감이 있는 엔티티는 archived라도 보여줌 — 마감은 상태보다 날짜가 우선
    if show_all:
        rows = conn.execute(
            "SELECT id, filename, deadline_date, urgency, phase FROM entities "
            "WHERE deadline_date IS NOT NULL AND phase NOT IN ('dissolved','sediment') "
            "ORDER BY deadline_date"
        ).fetchall()
    else:
        cutoff = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT id, filename, deadline_date, urgency, phase FROM entities "
            "WHERE deadline_date IS NOT NULL AND deadline_date >= ? AND deadline_date <= ? "
            "AND phase NOT IN ('dissolved','sediment') "
            "ORDER BY deadline_date",
            (today, cutoff)
        ).fetchall()
    conn.close()
    if not rows:
        print("  마감 없음")
        return
    print(f"\n  === 마감 ({len(rows)}건) ===\n")
    for r in rows:
        delta = (datetime.strptime(r["deadline_date"], "%Y-%m-%d").date() - datetime.now().date()).days
        if delta < 0:
            label = "지남"
        elif delta == 0:
            label = "오늘"
        elif delta == 1:
            label = "내일"
        else:
            label = f"D-{delta}"
        name = r["filename"].replace(".md", "")
        # 파일명 정제: 날짜 프리픽스, ADR 번호, 언더스코어 제거
        name = re.sub(r'^\d{8}_?', '', name)
        name = re.sub(r'^마감_', '', name)
        name = re.sub(r'SC41 마감 ', '', name)
        name = re.sub(r'_?\d{6}$', '', name)  # 타임스탬프 접미사
        name = re.sub(r'\s*\d{8,}', '', name)  # 남은 긴 숫자열
        name = name.replace("_", " ").strip()[:40]
        urg = " *긴급*" if r["urgency"] == "high" else ""
        print(f"    {label:6s} {r['deadline_date']} {name}{urg}")

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
    elif c in ("rebuild-fts","rebuild_fts"): cmd_rebuild_fts()
    elif c=="orphans": cmd_orphans()
    elif c=="do" and len(sys.argv)>2: cmd_compose(" ".join(sys.argv[2:]))
    elif c=="idea" and len(sys.argv)>2: cmd_capture(" ".join(sys.argv[2:]))
    elif c=="ipc": ipc_cli(sys.argv[2:])
    elif c in ("claim","claim-file","sessions","release","check-conflicts"):
        session_lock_cli([c] + sys.argv[2:])
    elif c=="check" and len(sys.argv)>=3:
        session_lock_cli(["check", sys.argv[2]])
    elif c=="deadlines": cmd_deadlines(show_all="--all" in sys.argv)
    else: print(f"  알 수 없는 명령: {c}"); print(USAGE)

if __name__ == "__main__":
    main()
