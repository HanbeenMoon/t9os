"""
T9 OS Seed — extended command module (split from t9_seed.py to maintain line cap)
cmd_reflect, cmd_consolidate, cmd_watch, cmd_history, cmd_relate,
cmd_digest_index, cmd_legacy, cmd_ingest, cmd_resurface, cmd_rebuild_fts, cmd_orphans

Circular import prevention: does not import t9_seed.py.
Common dependencies come from function args or lib.*.
"""
import sys, json, sqlite3, time, hashlib, logging
from datetime import datetime, timedelta
from pathlib import Path

from lib.parsers import parse_md, write_md
from lib.config import DB_PATH

_log = logging.getLogger("t9_seed")

# ─── Path constants (t9_seed.py ,  import   declaration) ────────────────────────────────────────
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
    if not trans: print("  not found.\n"); conn.close(); return
    comp = [t for t in trans if t["to_phase"]=="archived"]
    diss = [t for t in trans if t["to_phase"]=="dissolved"]
    susp = [t for t in trans if t["to_phase"]=="suspended"]
    prom = [t for t in trans if t["to_phase"] in ("individuating","stabilized","candidate_generated","tension_detected")]
    print(f"  {len(trans)}items: completed {len(comp)}, {len(diss)}, suspended {len(susp)}, {len(prom)}")
    if comp:
        print("  completed:"); [print(f"    {t['filename'][:50]}") for t in comp]
    if diss:
        print("  :"); [print(f"    {t['filename'][:50]} ({t['reason'] or '-'})") for t in diss]
    sug = []
    if not comp: sug.append("completed 0items -- WIP  ")
    if len(prom)>=5 and not comp: sug.append("  completed not found")
    if len(diss)>=3: sug.append(f" {len(diss)}items -- scope  ")
    if sug:
        print("  suggestion:"); [print(f"    * {s}") for s in sug]
    LEARNED_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = f"\n## weekly reflection -- {now:%Y-%m-%d}\n- : {len(trans)}items (completed{len(comp)}/{len(diss)}/suspended{len(susp)})\n"
    for s in sug: entry += f"- {s}\n"
    existing = LEARNED_PATH.read_text(encoding="utf-8") if LEARNED_PATH.exists() else "# T9 LEARNED\n\n"
    LEARNED_PATH.write_bytes((existing+entry+"\n").encode("utf-8"))
    print(f"\n  record: {LEARNED_PATH.relative_to(T9)}\n"); conn.close()


def cmd_consolidate(get_db, fhash, _upsert, _preview_len):
    conn = get_db()
    print(f"\n  === T9 Memory Consolidation ===\n")
    archived = conn.execute("SELECT * FROM entities WHERE phase IN ('archived','dissolved') ORDER BY updated_at DESC").fetchall()
    if not archived: print("  archive not found.\n"); conn.close(); return
    MEMORY.mkdir(parents=True, exist_ok=True)
    groups = {}
    for it in archived:
        # column concepts , fallbackmetadata
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
        sec = f"\n## Integrate -- {datetime.now():%Y-%m-%d %H:%M}\n\n"
        for i in new:
            sec += f"- <!-- eid:{i['id']} --> **{i['filename']}** ({i['phase']})\n"
            pv = (i["body_preview"] or "")[:80].replace("\n"," ")
            if pv: sec += f"  > {pv}\n"
        mp.write_bytes((ex+sec+"\n").encode("utf-8")); total += len(new)
        print(f"  [{concept}] {len(new)}items -> memory_{concept}.md")
    for md in MEMORY.glob("*.md"):
        if not md.name.startswith("."):
            try:
                m2, b2 = parse_md(md)
                _upsert(conn, f"memory/{md.name}", md.name, m2.get("phase","stabilized"),
                        json.dumps(m2, ensure_ascii=False), b2[:500], fhash(md))
            except Exception as e:
                _log.debug("consolidate parse failed for %s: %s", md.name, e)
    conn.commit(); conn.close()
    print(f"\n  {total}items Integrate.\n")


def cmd_watch(get_db, fhash, cmd_reindex, interval=5):
    print(f"\n  === T9 file monitoring ({interval}) ===\n  Ctrl+C end\n")
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
                if p not in prev or prev[p]!=h: print(f"  [change] {p}"); ch=True
            for p in prev:
                if p not in curr: print(f"  [delete] {p}"); ch=True
            if ch: cmd_reindex()
            prev = curr
    except KeyboardInterrupt: print("\n  monitoring end.\n")


def cmd_history(get_db, eid):
    conn = get_db()
    row = conn.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
    if not row: print(f"  ID {eid} not found"); conn.close(); return
    print(f"\n  === transition history: [{eid}] {row['filename']} ===")
    print(f"  current: {row['phase']}  path: {row['filepath']}")
    if row["created_at"]:
        print(f"  Created: {row['created_at'][:16]}")
    if row["parent_id"]:
        print(f"  : [{row['parent_id']}]")
    if row["urgency"]:
        print(f"  Urgent: {row['urgency']}")
    if row["concepts"]:
        try:
            c = json.loads(row["concepts"])
            print(f"  Concepts: {', '.join(c)}")
        except Exception: pass
    m = json.loads(row["metadata"]) if row["metadata"] else {}
    rel = m.get("related_to", [])
    if rel: print(f"  connection (metadata): {rel}")
    # relates tablequery
    rels = conn.execute(
        "SELECT r.*, e1.filename as src_name, e2.filename as tgt_name "
        "FROM relates r "
        "LEFT JOIN entities e1 ON r.source_id=e1.id "
        "LEFT JOIN entities e2 ON r.target_id=e2.id "
        "WHERE r.source_id=? OR r.target_id=?", (eid, eid)
    ).fetchall()
    if rels:
        print(f"  (transduction):")
        for r in rels:
            arrow = "\u2192" if r["direction"] == "source_to_target" else "\u2194"
            desc = f" ({r['description']})" if r["description"] else ""
            print(f"    [{r['source_id']}] {r['src_name'] or '?'} {arrow} [{r['target_id']}] {r['tgt_name'] or '?'}{desc}")
    ts = conn.execute("SELECT * FROM transitions WHERE entity_id=? ORDER BY timestamp", (eid,)).fetchall()
    if ts:
        print()
        for t in ts:
            print(f"  {t['timestamp'][:16]}  {t['from_phase'] or '(start)'} -> {t['to_phase']}")
            if t["reason"]: print(f"                    reason: {t['reason']}")
    else: print("\n  transition history not found.")
    print(); conn.close()


def cmd_relate(get_db, self_check, id1, id2, direction="bidirectional", description=""):
    """entity relation. transduction record ().

    direction: "bidirectional" | "source_to_target" (id1->id2)
    description: "A pattern B  "  
    """
    conn = get_db()
    for eid in (id1, id2):
        row = conn.execute("SELECT id FROM entities WHERE id=?", (eid,)).fetchone()
        if not row: print(f"  ID {eid} not found"); conn.close(); return

    # relates tablerecord (transduction)
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

    # record
    if direction == "bidirectional":
        try:
            conn.execute(
                "INSERT OR REPLACE INTO relates (source_id, target_id, direction, description, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (id2, id1, "bidirectional", description, datetime.now().isoformat())
            )
        except Exception as e:
            _log.debug("reverse relate failed: %s", e)

    # existing metadatarelated_to(compatibility)
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
    print(f"  connection: [{id1}] {arrow} [{id2}]{desc_str}\n")


def cmd_digest_index(get_db, fhash, _upsert, _preview_len):
    """fileFTS"""
    conn = get_db()
    digest_dirs = [
        HANBEEN / "_legacy" / "_notion_dump" / "digested_final",
        HANBEEN / "_legacy" / "_personal_dump" / "digested_final",
    ]
    count = 0
    for ddir in digest_dirs:
        if not ddir.exists():
            print(f"  [SKIP] {ddir} not found")
            continue
        src_label = str(ddir.parent.name)
        for f in sorted(ddir.glob("*.txt")):
            body = f.read_text(encoding="utf-8", errors="replace")
            rel = f"digest/{f.name}"
            if _upsert(conn, rel, f.name, "stabilized",
                       json.dumps({"source": "digest", "type": src_label}, ensure_ascii=False),
                       body[:_preview_len(f, body)], fhash(f), full_body=body):
                count += 1
        print(f"  [{src_label}] completed")
    conn.commit(); conn.close()
    print(f"  {count}items completed")


def cmd_legacy(query):
    if not LEGACY_DB.exists(): print(f"  DB not found"); return
    conn = sqlite3.connect(str(LEGACY_DB)); conn.row_factory = sqlite3.Row
    rs = conn.execute("SELECT id,path,name,ext,dir,content_summary,ai_tags FROM files WHERE name LIKE ? OR path LIKE ? OR content_summary LIKE ? OR ai_tags LIKE ? ORDER BY modified DESC LIMIT 20",
        (f"%{query}%",)*4).fetchall()
    if not rs: print(f"  result not found: '{query}'")
    else:
        print(f"\n  === : '{query}' ({len(rs)}items) ===\n")
        for r in rs:
            print(f"  [{r['id']:4d}] {r['name'][:40]:40s} | {r['dir'] or '-'}")
            s = (r["content_summary"] or "")[:60].replace("\n"," ")
            if s: print(f"         {s}")
    conn.close(); print()


def cmd_ingest(cmd_capture, filepath):
    """/original filePreindividualregister."""
    import shutil
    fp = Path(filepath)
    if not fp.exists():
        print(f'  file not found: {filepath}'); return
    # 1. originalinboxcopy
    dest = FIELD / fp.name
    if not dest.exists():
        shutil.copy2(str(fp), str(dest))
        print(f'  original save: {dest.name}')
    # 2. — [name] [] message format
    text = fp.read_text(encoding='utf-8', errors='replace')
    messages = []
    for line in text.split(chr(10)):
        line = line.strip()
        if not line or line.startswith('---') or line == '\u3161': continue
        # [] [] content pattern
        if '] ' in line:
            parts = line.split('] ', 2)
            if len(parts) >= 3:
                msg = parts[-1].strip()
                if len(msg) > 15 and not msg.startswith(''):
                    messages.append(msg)
            elif len(parts) == 2:
                msg = parts[-1].strip()
                if len(msg) > 15 and not msg.startswith(''):
                    messages.append(msg)
    # 3. messagePreindividual register
    count = 0
    for msg in messages:
        if len(msg) > 20:  # items
            cmd_capture(msg)
            count += 1
    print(f'  {count}items Preindividual register completed (original {len(messages)}items )')


def cmd_resurface(get_db, keyword=""):
    """Sediment(sediment) state . key3~5, keysearch."""
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
        print("  Sediment not found." + (f" (key: {keyword})" if keyword else ""))
        conn.close(); return
    print(f"\n  === Sediment (resurface) ===" + (f" key: {keyword}" if keyword else " ") + f" ({len(results)}items)\n")
    for r in results:
        preview = (r["body_preview"] or "")[:80].replace("\n", " ")
        tags = ""
        if r["concepts"]:
            try: tags = ", ".join(json.loads(r["concepts"]))
            except Exception: pass
        print(f"  [{r['id']:3d}] {r['filename'][:50]}")
        if preview: print(f"         {preview}")
        if tags: print(f"         Concepts: {tags}")
        print(f"         final: {(r['updated_at'] or '')[:10]}")
        print()
    print("  : python3 t9_seed.py transition <id> reactivated\n")
    conn.close()


def cmd_rebuild_fts(get_db):
    """FTS5 index. search result missing use."""
    conn = get_db()
    print("  FTS5 index start...")
    try:
        conn.execute("DROP TABLE IF EXISTS entities_fts")
        conn.execute("CREATE VIRTUAL TABLE entities_fts USING fts5(filename, body_preview, metadata_text)")
    except Exception as e:
        print(f"  [ERROR] FTS5 table create failed: {e}")
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
    print(f"  FTS5 completed: {count}/{len(rows)}items ")


def cmd_orphans(get_db):
    """filereport. --fix sediment ."""
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
            # HANBEEN criteria
            fp2 = HANBEEN / r["filepath"]
            if not fp2.exists():
                orphans.append(r)
    if corrupted:
        print(f"\n  === DB {len(corrupted)}items (filepath) ===")
        for r in corrupted:
            print(f"  [{r['id']:4d}] filepath={repr(r['filepath'])}")
        if fix:
            for r in corrupted:
                conn.execute("DELETE FROM entities WHERE id=?", (r["id"],))
            conn.commit()
            print(f"  {len(corrupted)}items delete completed")
    if not orphans:
        print("  not found (file check)")
    else:
        print(f"\n  === {len(orphans)}items (file not found) ===\n")
        for r in orphans:
            print(f"  [{r['id']:4d}] {r['phase']:15s} | {r['filename'][:50]}")
            print(f"         path: {r['filepath']}")
        if fix:
            for r in orphans:
                conn.execute("UPDATE entities SET phase='sediment', updated_at=? WHERE id=?",
                    (datetime.now().isoformat(), r["id"]))
                conn.execute("INSERT INTO transitions (entity_id,from_phase,to_phase,timestamp,reason) VALUES(?,?,?,?,?)",
                    (r["id"], r["phase"], "sediment", datetime.now().isoformat(), "orphan: file missing"))
            conn.commit()
            print(f"\n  {len(orphans)}items → sediment completed")
        else:
            print(f"\n  --fix sediment : python3 t9_seed.py orphans --fix")
    conn.close()
