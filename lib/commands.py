"""
T9 OS Seed — extracted large command functions
cmd_daily, cmd_tidy, cmd_compose, cmd_approve + helpers
Extracted to maintain t9_seed.py 1000-line cap
"""
import json, shutil, re
from datetime import datetime, timedelta
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent
FIELD = T9 / "field" / "inbox"
ACTIVE = T9 / "spaces" / "active"


def _parse_deadlines(find_deadline_file_fn):
    """Parse deadlines. Search candidate paths for file, return empty list if not found."""
    deadline_file = find_deadline_file_fn()
    if not deadline_file:
        return []
    try:
        blocks = deadline_file.read_text(encoding="utf-8", errors="replace").split("===")
    except Exception:
        return []
    deadlines, today = [], datetime.now().date()
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        d = {}
        for line in block.split("\n"):
            if ":" in line:
                k, _, v = line.partition(":")
                d[k.strip()] = v.strip()
        if "date" in d and "title" in d:
            try:
                days = (datetime.strptime(d["date"], "%Y-%m-%d").date() - today).days
                if -1 <= days <= 14:
                    deadlines.append({"title": d["title"], "date": d["date"], "days": days, "urgent": d.get("urgent", "N") == "Y"})
            except ValueError:
                pass
    return sorted(deadlines, key=lambda x: x["days"])


def _show_calendar_events(now):
    """Read today's GoogleCalendar MD from field/inbox and display events."""
    cal_files = sorted(FIELD.glob(f"{now:%Y%m%d}_GoogleCalendar_*.md"))
    if not cal_files:
        return
    try:
        lines = [l for l in cal_files[-1].read_text(encoding="utf-8", errors="replace").split("\n") if l.startswith("- [")]
        if lines:
            print(f"  [Calendar] Events ({len(lines)}items):")
            for l in lines[:8]:
                print(f"    {l[2:]}")
            print()
    except Exception:
        pass


def cmd_daily(get_db, find_deadline_file_fn):
    """Daily brief: deadlines + individuating/tension counts + transductive learning suggestions."""
    conn = get_db()
    now = datetime.now()
    print(f"\n  === T9 OS Seed v0.2 -- {now:%Y-%m-%d %A} ===\n")

    dl = _parse_deadlines(find_deadline_file_fn)
    if dl:
        print("  [!] Deadlines:")
        for d in dl:
            lbl = {-1: "Yesterday!", 0: "Today!", 1: "Tomorrow"}.get(d["days"], f"D-{d['days']}")
            print(f"    {lbl:6s} {d['date']} {d['title']}{' *URGENT*' if d['urgent'] else ''}")
        print()
    else:
        print("  [Deadlines] No file found or no imminent deadlines\n")

    _show_calendar_events(now)

    urgent = conn.execute(
        "SELECT id,filename FROM entities WHERE phase NOT IN ('archived','sediment','dissolved') "
        "AND urgency='high'"
    ).fetchall()
    if urgent:
        print(f"  [!!] Urgent ({len(urgent)}items):")
        for r in urgent:
            print(f"    [{r['id']}] {r['filename'][:50]}")
        print()

    active = conn.execute("SELECT id,filename FROM entities WHERE phase IN ('individuating','stabilized')").fetchall()
    if active:
        print(f"  In progress ({len(active)}items):")
        for r in active:
            print(f"    [{r['id']}] {r['filename'][:50]}")
        print()

    ind_cnt = conn.execute("SELECT COUNT(*) as c FROM entities WHERE phase='individuating'").fetchone()["c"]
    stab_cnt = conn.execute("SELECT COUNT(*) as c FROM entities WHERE phase='stabilized'").fetchone()["c"]
    pre = conn.execute("SELECT COUNT(*) as c FROM entities WHERE phase='preindividual'").fetchone()["c"]
    tens = conn.execute("SELECT COUNT(*) as c FROM entities WHERE phase='tension_detected'").fetchone()["c"]
    imp = conn.execute("SELECT COUNT(*) as c FROM entities WHERE phase='impulse'").fetchone()["c"]
    sed = conn.execute("SELECT COUNT(*) as c FROM entities WHERE phase='sediment'").fetchone()["c"]
    print(f"  Preindividual: {pre}items | Impulse: {imp}items | Tension: {tens}items | Individuating: {ind_cnt}items | Stabilized: {stab_cnt}items")
    if sed > 0:
        print(f"  (Sediment: {sed}items — Preindividual, search)")

    stale = conn.execute("SELECT id,filename FROM entities WHERE phase='suspended' AND updated_at<? LIMIT 5",
                         ((now - timedelta(days=30)).strftime("%Y-%m-%d"),)).fetchall()
    if stale:
        print(f"\n  [?] 30d+ suspended:")
        for r in stale:
            print(f"    [{r['id']}] {r['filename'][:50]}")

    recent_archived = conn.execute(
        "SELECT id,filename,concepts,metadata FROM entities "
        "WHERE phase='archived' AND updated_at>=? ORDER BY updated_at DESC LIMIT 5",
        ((now - timedelta(days=14)).strftime("%Y-%m-%d"),)
    ).fetchall()
    if recent_archived:
        print(f"\n  [Transductive learning] Extractable patterns from recently archived entities:")
        for r in recent_archived:
            concepts = []
            if r["concepts"]:
                try:
                    concepts = json.loads(r["concepts"])
                except Exception:
                    pass
            if not concepts:
                m = json.loads(r["metadata"]) if r["metadata"] else {}
                concepts = m.get("concepts", [])
            if concepts:
                print(f"    [{r['id']}] {r['filename'][:40]} → Concepts: {', '.join(concepts)}")
                for c in concepts:
                    related = conn.execute(
                        "SELECT id,filename FROM entities WHERE phase IN ('individuating','tension_detected') "
                        "AND (concepts LIKE ? OR metadata LIKE ?) AND id!=? LIMIT 2",
                        (f'%"{c}"%', f'%"{c}"%', r["id"])
                    ).fetchall()
                    if related:
                        for rel in related:
                            print(f"      → [{rel['id']}] {rel['filename'][:40]}— transducible")

    # Sediment resurface: 1~2items
    if sed > 0:
        import random
        sed_items = conn.execute(
            "SELECT id,filename,body_preview FROM entities WHERE phase='sediment'"
        ).fetchall()
        if sed_items:
            sample = random.sample(list(sed_items), min(2, len(sed_items)))
            print(f"\n  [] SedimentPreindividual:")
            for s in sample:
                preview = (s["body_preview"] or "")[:60].replace("\n", " ")
                print(f"    [{s['id']}] {s['filename'][:45]}")
                if preview:
                    print(f"         {preview}")
            print(f"    → use resurface command to explore more")

    conn.close()
    print()


def cmd_tidy(get_db, cmd_transition_fn):
    """Periodic tidy: resolve inbox phase-directory mismatch + 30d+ preindividual sedimentation.
    Simondon principle: preindividuals are never deleted. They sediment (sink into strata)."""
    conn = get_db()
    now = datetime.now()
    moved = []
    sedimented = []

    # 1. stabilizedinbox→ archived
    stab_inbox = conn.execute(
        "SELECT id, filename, filepath FROM entities "
        "WHERE phase='stabilized' AND filepath LIKE 'field/inbox%'"
    ).fetchall()
    conn.close()
    for ent in stab_inbox:
        name = ent["filename"].replace(".md", "")[:40]
        cmd_transition_fn(ent["id"], "archived", "tidy: stabilized→archived autoclean up")
        moved.append(f"  `{name}` → archived")

    # 2. individuatinginbox→ activefile move
    conn = get_db()
    ind_inbox = conn.execute(
        "SELECT id, filename, filepath FROM entities "
        "WHERE phase='individuating' AND filepath LIKE 'field/inbox%'"
    ).fetchall()
    for ent in ind_inbox:
        old_path = T9 / ent["filepath"]
        if not old_path.exists():
            continue
        ACTIVE.mkdir(parents=True, exist_ok=True)
        new_path = ACTIVE / old_path.name
        if not new_path.exists():
            shutil.move(str(old_path), str(new_path))
            new_rel = str(new_path.relative_to(T9))
            conn.execute("UPDATE entities SET filepath=?, updated_at=? WHERE id=?",
                         (new_rel, now.isoformat(), ent["id"]))
            name = ent["filename"].replace(".md", "")[:40]
            moved.append(f"  `{name}` → active")

    # 3. 30+ preindividual → sediment (Sediment: delete )
    stale_cutoff = (now - timedelta(days=30)).isoformat()
    stale_pre = conn.execute(
        "SELECT id, filename, filepath FROM entities "
        "WHERE phase='preindividual' AND updated_at < ? AND filepath LIKE 'field/inbox%'",
        (stale_cutoff,)
    ).fetchall()
    conn.close()
    for ent in stale_pre:
        name = ent["filename"].replace(".md", "")[:40]
        cmd_transition_fn(ent["id"], "sediment", "tidy: 30+ Preindividual → Sediment ( )")
        sedimented.append(f"  `{name}`")

    # 4. output
    print(f"\n  === T9 Tidy ({now:%Y-%m-%d %H:%M}) ===")
    print(f"  Moved: {len(moved)}items, Sediment: {len(sedimented)}items")
    for m in moved:
        print(m)
    for s in sedimented:
        print(f"  [Sediment] {s}")
    if not moved and not sedimented:
        print("  Nothing to tidy")

    # 5. Telegram report ()
    if moved or sedimented:
        try:
            import sys as _sys
            _sys.path.insert(0, str(T9 / "pipes"))
            from tg_common import tg_send
            lines = [f"T9 Tidy — {now:%m/%d %H:%M}"]
            if moved:
                lines.append(f"\nmove {len(moved)}items:")
                lines.extend(moved[:10])
            if sedimented:
                lines.append(f"\nSediment {len(sedimented)}items ( ):")
                lines.extend(sedimented[:10])
            tg_send("\n".join(lines))
        except Exception as e:
            print(f"  [Notification failed] {e}")


def cmd_compose(text, extract_concepts_fn, detect_urgency_fn, detect_tension_fn):
    """Dynamic plan generation. Adaptive based on concepts/urgency/disparation."""
    concepts, urgency = extract_concepts_fn(text), detect_urgency_fn(text)
    has_tension, dim_a, dim_b = detect_tension_fn(text)

    print(f"\n  === T9 Composer v0.2 ===")
    print(f"  Input: {text}")
    print(f"  Concepts: {', '.join(concepts) or '(free-form)'}  Urgent: {urgency}")
    if has_tension:
        print(f"  Tension: {dim_a} vs {dim_b}")
    print()

    plans = []

    if urgency == "high":
        plans.append({"id": "A", "name": "Immediate execution (minimum path)",
                       "steps": ["1. Core deliverable in 30 min", "2. Deploy without verification", "3. Post-hoc improvement"],
                       "time": "30 min", "tool": "cc"})
    else:
        plans.append({"id": "A", "name": "Direct execution (standard path)",
                       "steps": ["1. Check existing resources", "2. Create core deliverable", "3. Verify then complete"],
                       "time": "1 hour", "tool": "cc"})

    if "explore" in concepts or "become" in concepts:
        plans.append({"id": "B", "name": "Explore-learn loop",
                       "steps": ["1. Collect 3 sources (gm parallel)", "2. Extract key insights", "3. Derive applicable patterns"],
                       "time": "1.5 hours", "tool": "gm+cc"})
    elif "create" in concepts or "solve" in concepts:
        plans.append({"id": "B", "name": "Split parallel execution",
                       "steps": ["1. Decompose subtasks", "2. cc/cx parallel assignment", "3. Integrate and verify"],
                       "time": "1 hour", "tool": "cc+cx"})
    elif "earn" in concepts:
        plans.append({"id": "B", "name": "ROI-first execution",
                       "steps": ["1. Cost-benefit assessment", "2. Select minimum-input option", "3. Quick verification"],
                       "time": "45 min", "tool": "cc"})
    else:
        plans.append({"id": "B", "name": "Parallel split",
                       "steps": ["1. Decompose subtasks", "2. cc/cx parallel assignment", "3. Integrate"],
                       "time": "1 hour", "tool": "cc+cx"})

    if has_tension:
        plans.append({"id": "C", "name": f"Tension  ({dim_a} vs {dim_b})",
                       "steps": [f"1. {dim_a} requirements analysis", f"2. {dim_b} requirements analysis",
                                 "3. Derive compatible solution (transduction)"],
                       "time": "1 hour", "tool": "cc"})
    else:
        plans.append({"id": "C", "name": "Buy-first exploration",
                       "steps": ["1. Search 3 existing services/tools", "2. Cost-effectiveness evaluation", "3. Select and apply"],
                       "time": "45 min", "tool": "gm"})

    for p in plans:
        print(f"  -- Plan {p['id']}: {p['name']} ({p['time']}, {p['tool']}) --")
        for s in p["steps"]:
            print(f"     {s}")
        print()

    cid = f"{datetime.now():%Y%m%d_%H%M%S}"
    cdir = T9 / "data" / "composes"
    cdir.mkdir(parents=True, exist_ok=True)
    compose_data = {
        "id": cid, "text": text, "concepts": concepts, "urgency": urgency,
        "plans": plans, "created": datetime.now().isoformat(), "approved": None,
    }
    if has_tension:
        compose_data["disparation"] = {"dimension_a": dim_a, "dimension_b": dim_b}
    (cdir / f"{cid}.json").write_bytes(json.dumps(compose_data, ensure_ascii=False, indent=2).encode("utf-8"))
    plan_ids = "/".join(p["id"] for p in plans)
    print(f"  Compose ID: {cid}\n  Approve: python3 t9_seed.py approve {cid} {plan_ids}\n")


def cmd_approve(cid, choice, self_check_fn, write_md_fn, index_file_fn):
    """Approve plan → create active entity."""
    cf = T9 / "data" / "composes" / f"{cid}.json"
    if not cf.exists():
        print(f"  ID '{cid}' not found")
        return
    data = json.loads(cf.read_text(encoding="utf-8"))
    sel = next((p for p in data["plans"] if p["id"] == choice.upper()), None)
    if not sel:
        valid_ids = "/".join(p["id"] for p in data["plans"])
        print(f"  Plan '{choice}' not found (valid: {valid_ids})")
        return
    now = datetime.now()
    safe = re.sub(r'[^\w\s-]', '', data["text"][:30]).strip()
    fp = ACTIVE / f"{now:%Y%m%d}_{safe}_{now:%H%M%S}.md"
    ACTIVE.mkdir(parents=True, exist_ok=True)
    meta = {"phase": "individuating", "created": f"{now:%Y-%m-%d %H:%M}", "concepts": data.get("concepts", []),
            "urgency": data.get("urgency", "mid"), "compose_id": cid, "plan": choice.upper()}
    if data.get("disparation"):
        meta["disparation"] = data["disparation"]
    body = f"# {data['text']}\n\n## Plan {sel['id']}: {sel['name']}\n\n" + "".join(f"- [ ] {s}\n" for s in sel["steps"])
    self_check_fn("approve", meta)
    write_md_fn(fp, meta, body)
    index_file_fn(fp)
    data["approved"] = {"plan": choice.upper(), "timestamp": now.isoformat()}
    cf.write_bytes(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    print(f"  Approved: Plan {choice.upper()}, Created: {fp.name}\n")
