#!/usr/bin/env python3
"""
T9 OS Seed v0.2 -- Simondonian Engine (refactored)
"The starting point is not Task but Tension."
NO "project" field. NO hardcoded classification.

v0.2: DB enhancement, disparation, transduction, dynamic compose, digest indexing
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
from lib.config import DB_PATH  # WSL native DB (NTFS lock prevention)
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
SEDIMENT = T9/"spaces"/"sediment"  # sediment: sinking not deletion. Searchable, excluded from daily
LEGACY_DB = T9/".t9_legacy.db"

# Deadlines: DB (entities.deadline_date) is the single source.
# Legacy fallback kept, but daily uses DB first.
DEADLINE_CANDIDATES = [
    T9/"data"/"notion_dump"/"T9_deadlines.txt",       # legacy fallback (pending removal)
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
# PROJECTS scanned only during full reindex (too heavy for heartbeat)
SCAN_DIRS_HEAVY = [PROJECTS]  # scanned only during full reindex
SCAN_DIRS_LIGHT = []  # currently unused
SCAN_EXTS = {".md", ".docx", ".xlsx", ".pdf", ".hwp", ".txt", ".csv", ".log",
             ".zip", ".jpg", ".jpeg", ".png", ".mp4", ".svg"}

# Simondon phase -> directory mapping (impulse added)
PHASE_DIR = {
    "preindividual": FIELD, "impulse": IMPULSES,
    "tension_detected": FIELD, "candidate_generated": FIELD,
    "individuating": ACTIVE, "stabilized": ACTIVE, "split": ACTIVE,
    "merged": ACTIVE, "reactivated": ACTIVE,
    "suspended": SUSPENDED, "archived": ARCHIVED, "dissolved": ARCHIVED,
    "sediment": SEDIMENT,  # sediment: preindividual sunk into strata
}

# body_preview length: adaptive based on content
def _preview_len(filepath, body=None):
    """
    Adaptively determine body_preview length based on file type and content density.
    - Session conversations: purest preindividual data, needs generous preview
    - Short files: full text as-is
    - Long high-density files (decisions, briefs): generous
    - Long repetitive files (logs, CSV): short
    """
    if body is None:
        body = ""
    total = len(body)

    # Short files: keep full text (no reason to truncate)
    if total <= 1000:
        return total

    s = str(filepath)

    # Session conversations = purest preindividual data
    if 'conversations' in s:
        # Proportional to conversation length, max 5000 chars
        return min(total, max(3000, total // 3))

    # Briefs/decisions = high information density, keep close to full text
    if any(k in s for k in ['session-briefs', 'brief', 'decisions', 'WORKING', 'BIBLE']):
        return min(total, 3000)

    # Structured documents (constitution, telos) = focus on front section
    if any(k in s for k in ['constitution', 'telos', 'artifacts']):
        return min(total, 2000)

    # Data files (CSV, logs) = front portion only
    if any(s.endswith(ext) for ext in ['.csv', '.log', '.txt']):
        return min(total, 500)

    # Default: half of file length, min 500 max 2000
    return min(total, max(500, total // 2))

# State transition graph (enhanced: split/merged/reactivated paths)
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
    "sediment":            {"reactivated"},  # can resurface (reactivate) from sediment
    "dissolved":           {"sediment"},     # existing dissolved can also transition to sediment
}

CONCEPT_KW = {
    "create":  ["build","create","implement","develop","make"],
    "explore": ["research","explore","investigate","analyze"],
    "solve":   ["fix","solve","debug","resolve","repair"],
    "earn":    ["revenue","money","earn","sales","business"],
    "express": ["present","write","express","essay","publish"],
    "become":  ["study","learn","become","grow","learning"],
}
# urgency is not inferred from keywords. Set explicitly by designer or based on deadlines only.
URGENCY_KW = {}

USAGE = """  Usage: python3 t9_seed.py <command> [args]
  capture/idea <text>   Save preindividual
  reindex               File -> DB sync
  search <query>        Search
  status                Overall status
  daily                 Daily brief
  transition <id> <phase> [reason]
  compose/do <text>     Create plan
  approve <id> <plan>   Approve plan
  reflect               Weekly reflection
  consolidate           Archive -> memory integration
  history <id>          Transition history
  relate <id1> <id2>    Connect entities
  legacy <query>        Legacy DB search
  ipc <cmd>             Inter-session communication
  claim <project> [desc] Project claim
  claim-file <path>     File claim
  sessions              Active session list
  release [project]     Release claim
  check <path>          File conflict check
  done <id>             -> stabilized
  go <id>               -> individuating
  resurface [keyword]   Resurface sediment entities (random 3-5 or keyword search)
  tidy                  Periodic cleanup (auto: inbox->active/archived)
  rebuild-fts           Rebuild FTS5 search index completely
  orphans [--fix]       Detect orphan entities (DB records without files). --fix to sediment"""

# --- File parsing ---

# --- DB ---

# Enhanced regular column list (migration targets)
_EXTRA_COLUMNS = {
    "created_at": "TEXT",      # preindividual entry time
    "parent_id":  "INTEGER",   # split/merged relationship tracking
    "urgency":    "TEXT",      # high/mid/low (regular column)
    "concepts":   "TEXT",      # JSON array (regular column)
    "deadline_date": "TEXT",   # ISO date (2026-04-04). Filter entities with deadlines for schedule view.
}

def _migrate_db(conn):
    """Add missing columns via ALTER TABLE if needed. DROP TABLE absolutely prohibited."""
    existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(entities)").fetchall()}
    for col, ctype in _EXTRA_COLUMNS.items():
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE entities ADD COLUMN {col} {ctype}")
    # relates table (for transduction records)
    conn.execute("""CREATE TABLE IF NOT EXISTS relates (
        id INTEGER PRIMARY KEY,
        source_id INTEGER NOT NULL,
        target_id INTEGER NOT NULL,
        direction TEXT DEFAULT 'bidirectional',
        description TEXT,
        created_at TEXT,
        UNIQUE(source_id, target_id)
    )""")
    # Add direction column to relates if missing
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
    # Migration: regular columns + relates table
    _migrate_db(conn)
    return conn

# --- Utilities ---

def fhash(filepath):
    return hashlib.md5(Path(filepath).read_bytes()).hexdigest()[:12]

def self_check(op="write", meta=None):
    """Schema violation check. Regular columns are in the allow list."""
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
    """Urgency is not inferred from keywords. Set explicitly by designer or based on deadlines only."""
    return None

def _detect_tension(text):
    """Detect tension (disparation) in text. Returns True if opposing keyword pairs co-exist."""
    tl = text.lower()
    # Opposition dimensions: (dimension_a keywords, dimension_b keywords)
    oppositions = [
        (["fast","urgent","asap","rush","now"], ["slow","later","leisure","someday","long-term"]),
        (["build","make","implement","develop"], ["buy","purchase","outsource","service"]),
        (["simple","minimal","lean"], ["complex","perfect","elaborate"]),
        (["solo","alone"], ["collaborate","team","together"]),
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
    """Find deadline file from multiple candidate paths. Returns None if not found (no empty file creation)."""
    for candidate in DEADLINE_CANDIDATES:
        if candidate.exists():
            return candidate
        # Check for broken symlinks
        if candidate.is_symlink():
            continue
    return None

# --- DB upsert ---

def _upsert(conn, rel, fname, phase, meta_json, preview, h, full_body="",
            created_at=None, parent_id=None, urgency=None, concepts=None):
    now = datetime.now().isoformat()
    row = conn.execute("SELECT id, file_hash FROM entities WHERE filepath=?", (rel,)).fetchone()
    if row and row["file_hash"] == h: return False

    # Convert concepts to JSON array string
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
    """Build entity payload from file -- common logic."""
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

# --- Commands ---

def cmd_capture(text):
    """Save preindividual. Records disparation metadata when tension is detected."""
    now = datetime.now()
    title = re.sub(r'[^\w\s]', '', text[:30]).strip() or f"tension_{now:%H%M%S}"
    filepath = FIELD / f"{now:%Y%m%d}_{title}_{now:%H%M%S}.md"
    FIELD.mkdir(parents=True, exist_ok=True)
    concepts, urgency = extract_concepts(text), detect_urgency(text)

    meta = {
        "phase": "preindividual",
        "created": f"{now:%Y-%m-%d %H:%M}",
        "concepts": concepts,
        "urgency": urgency,
    }

    # Tension detection -> disparation record
    has_tension, dim_a, dim_b = _detect_tension(text)
    if has_tension:
        meta["disparation"] = {
            "dimension_a": dim_a,
            "dimension_b": dim_b,
            "resolution": "",  # recorded manually when resolved
        }
        meta["phase"] = "tension_detected"
        print(f"  [!] Tension detected: {dim_a} vs {dim_b}")

    # Auto-detect deadline date
    try:
        from lib.deadline_harvest import extract_date
        deadline = extract_date(text)
        if deadline:
            meta["deadline_date"] = deadline
            print(f"  [deadline detected] {deadline}")
    except Exception:
        deadline = None

    write_md(filepath, meta, text)
    self_check("capture", meta)
    print(f"  Saved: {filepath.name}")
    if concepts: print(f"  Concepts: {', '.join(concepts)}")

    # Transduction auto-detection: run before _index_file to prevent self-match
    try:
        conn = get_db()
        transductions = find_transductions(conn, concepts, text)
        report = format_transduction_report(transductions)
        if report:
            print(report)
    except Exception as e:
        print(f"  [warn] transduction detection failed: {e}", file=__import__('sys').stderr)

    _index_file(filepath)

    # Record deadline_date directly in DB column
    if deadline:
        try:
            conn = get_db()
            rel = str(filepath.relative_to(T9))
            conn.execute("UPDATE entities SET deadline_date=? WHERE filepath=?", (deadline, rel))
            conn.commit(); conn.close()
        except Exception:
            pass

    # Instant title refinement (Gemini Flash) -- at capture time, no 6-hour wait
    try:
        from pipes.t9_auto import gemini_call
        now_str = datetime.now().strftime("%Y-%m-%d")
        refine_prompt = (
            f'Extract a clean title (1 line) from the following text. Format dates as YYYY-MM-DD. '
            f'Today is {now_str}. Respond in JSON only: {{"title":"the title","date":"YYYY-MM-DD or null"}}\n\n'
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
                    # Only set deadline_date when deadline keywords are present (prevent false positives)
                    _fn = row["filename"] if "filename" in row.keys() else ""
                    _bp = row["body_preview"] if "body_preview" in row.keys() else ""
                    if (parsed.get("date") and parsed["date"] != "null"
                            and re.match(r'\d{4}-\d{2}-\d{2}', str(parsed["date"]))
                            and re.search(r'deadline|due|submit|exam', (_fn or "") + (_bp or ""), re.IGNORECASE)):
                        conn.execute("UPDATE entities SET deadline_date=? WHERE id=?", (parsed["date"], row["id"]))
                    conn.execute("UPDATE entities SET metadata=? WHERE id=?",
                                 (_json.dumps(meta_db, ensure_ascii=False), row["id"]))
                    conn.commit()
                    dt = parsed.get("title", "")
                    if dt:
                        print(f"  [refined] {dt}")
                conn.close()
    except Exception:
        pass  # capture proceeds normally even if Gemini fails

def cmd_reindex(incremental=False):
    conn = get_db()
    existing = {r["filepath"]: r["file_hash"] for r in conn.execute("SELECT filepath, file_hash FROM entities").fetchall()}
    found, count, skipped = set(), 0, 0
    # All directories + T9 root scan
    sources = [(sd, True, SCAN_EXTS) for sd in SCAN_DIRS] + [(T9, False, SCAN_EXTS)]
    # Light scan (MD only)
    for ld in SCAN_DIRS_LIGHT:
        sources.append((ld, True, {".md", ".txt"}))
    # Heavy directories: full reindex only (not incremental)
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
                # Incremental mode: skip if hash matches (saves parsing)
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
    # Protect data outside scan scope (digests etc) -- exclude from delete targets
    PROTECTED_PREFIXES = ("_legacy/", "memory/memory_")
    for d in set(existing.keys()) - found:
        if any(d.startswith(p) for p in PROTECTED_PREFIXES):
            continue  # protect manually registered data
        conn.execute("DELETE FROM entities WHERE filepath=?", (d,)); count += 1
    conn.commit()
    # Harvest deadlines: integrate deadline_date from multiple sources
    try:
        from lib.deadline_harvest import harvest_deadlines
        dl_count = harvest_deadlines(conn)
        if dl_count > 0:
            print(f"  Deadline harvest: {dl_count} items")
    except Exception as e:
        _log.warning("deadline harvest failed: %s", e)
    conn.close()
    self_check("reindex")
    print(f"  Scanned: {len(found)} items, updated: {count} items")

def cmd_search(query):
    conn = get_db()
    # LIKE search (sorted by recency + relevance)
    results = conn.execute(
        "SELECT id,filename,phase,metadata,urgency,concepts FROM entities "
        "WHERE filename LIKE ? OR body_preview LIKE ? OR concepts LIKE ? OR metadata LIKE ? "
        "ORDER BY "
        "  CASE WHEN filename LIKE ? THEN 0 ELSE 1 END, "  # filename match priority
        "  CASE WHEN phase='stabilized' THEN 0 WHEN phase='tension_detected' THEN 1 ELSE 2 END, "
        "  id DESC "
        "LIMIT 40",
        (f"%{query}%",)*4 + (f"%{query}%",)).fetchall()
    if not results: print("  No results found")
    else:
        for r in results:
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
    print(f"\n  === T9 OS Seed v0.2 (total {total} items) ===\n")
    for r in phases:
        print(f"  {r['phase']:20s} {r['cnt']:4d}  {'#'*min(r['cnt'],30)}")
    # Relation (relates) count
    rel_count = conn.execute("SELECT COUNT(*) as c FROM relates").fetchone()["c"]
    if rel_count:
        print(f"\n  Relations (transduction): {rel_count} items")
    conn.close()

def _is_movable(filepath_rel):
    """Check if file is movable. Only files in PHASE_DIR-mapped folders can be moved.
    Files in structural folders (constitution/, telos/) stay in place by design."""
    movable_roots = {str(d.relative_to(T9)).split("/")[0] for d in PHASE_DIR.values() if d != T9}
    first_part = Path(filepath_rel).parts[0] if Path(filepath_rel).parts else ""
    return first_part in movable_roots

def cmd_transition(eid, to_phase, reason=""):
    conn = get_db()
    row = conn.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
    if not row: print(f"  ID {eid} not found"); conn.close(); return
    fp = row["phase"]
    if to_phase not in TRANSITIONS.get(fp, set()):
        print(f"  Transition not allowed: {fp} -> {to_phase}  Allowed: {', '.join(TRANSITIONS.get(fp,set()))}"); conn.close(); return
    old_path = T9 / row["filepath"]
    is_protected = not _is_movable(row["filepath"])
    # Protected files: update DB phase only, no file move
    if is_protected:
        meta = json.loads(row["metadata"]) if row["metadata"] else {}
        meta["phase"], meta["transitioned_at"] = to_phase, f"{datetime.now():%Y-%m-%d %H:%M}"
        if old_path.suffix == ".md" and old_path.exists():
            _, body = parse_md(old_path)
            write_md(old_path, meta, body)  # update metadata in place
        new_rel = row["filepath"]  # no path change
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
                # WSL->NTFS cross-filesystem: copy+delete fallback
                shutil.copy2(str(old_path), str(new_path))
                try:
                    old_path.unlink()
                except PermissionError:
                    pass  # DB updates to new path even if original delete fails
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
    """Deadline view -- filter entities with deadline_date only."""
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    # Show entities with deadlines even if archived -- deadline priority is date, not state
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
        print("  No deadlines")
        return
    print(f"\n  === Deadlines ({len(rows)} items) ===\n")
    for r in rows:
        delta = (datetime.strptime(r["deadline_date"], "%Y-%m-%d").date() - datetime.now().date()).days
        if delta < 0:
            label = "Past"
        elif delta == 0:
            label = "Today"
        elif delta == 1:
            label = "Tmrw"
        else:
            label = f"D-{delta}"
        name = r["filename"].replace(".md", "")
        # Clean filename: remove date prefix, timestamps, underscores
        name = re.sub(r'^\d{8}_?', '', name)
        name = re.sub(r'^deadline_', '', name)
        name = re.sub(r'_?\d{6}$', '', name)  # timestamp suffix
        name = re.sub(r'\s*\d{8,}', '', name)  # remaining long number strings
        name = name.replace("_", " ").strip()[:40]
        urg = " *URGENT*" if r["urgency"] == "high" else ""
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
    elif c=="done" and len(sys.argv)>=3: cmd_transition(int(sys.argv[2]), "stabilized", " ".join(sys.argv[3:]) if len(sys.argv)>3 else "completed")
    elif c=="go" and len(sys.argv)>=3: cmd_transition(int(sys.argv[2]), "individuating", " ".join(sys.argv[3:]) if len(sys.argv)>3 else "started")
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
    else: print(f"  Unknown command: {c}"); print(USAGE)

if __name__ == "__main__":
    main()
