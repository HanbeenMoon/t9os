#!/usr/bin/env python3
"""T9 CEO Brief — Telegram report.
deadline , CEO.
."""
import sys, sqlite3
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import T9, HANBEEN, DB_PATH
from lib.logger import pipeline_run

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tg_common import tg_send


def _get_db():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def _get_deadlines():
    """state.mdseed dailydeadline extract"""
    state_path = HANBEEN / ".claude" / "state.md"
    if not state_path.exists():
        return []
    import re
    content = state_path.read_text(encoding="utf-8", errors="replace")
    results = []
    today = datetime.now().date()
    # D-N pattern date pattern
    for line in content.split("\n"):
        # "- D-7 2026-03-24 deadline" pattern
        m = re.search(r'(\d{4}-\d{2}-\d{2})\s+(.+?)(?:\s$)', line)
        if m:
            try:
                d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                delta = (d - today).days
                if -3 <= delta <= 14:
                    results.append((delta, m.group(1), m.group(2).strip()))
            except ValueError:
                pass
    # seed DBurgency=high deadline extract
    conn = _get_db()
    if conn:
        try:
            rows = conn.execute(
                "SELECT filename, metadata FROM entities "
                "WHERE phase NOT IN ('archived','dissolved','stabilized','sediment') "
                "AND metadata LIKE '%deadline%'"
            ).fetchall()
            for r in rows:
                meta = r["metadata"] or ""
                dm = re.search(r'(\d{4}-\d{2}-\d{2})', meta)
                if dm:
                    try:
                        d = datetime.strptime(dm.group(1), "%Y-%m-%d").date()
                        delta = (d - today).days
                        if -3 <= delta <= 7:
                            name = r["filename"].replace(".md", "")[:50]
                            if not any(name in x[2] for x in results):
                                results.append((delta, dm.group(1), name))
                    except ValueError:
                        pass
        except Exception:
            pass
        conn.close()
    return sorted(set(results))


def build_brief():
    now = datetime.now()
    sections = []

    # === 1. deadline (D-3 ) — ===
    deadlines = _get_deadlines()
    urgent_dl = [d for d in deadlines if d[0] <= 3]
    if urgent_dl:
        lines = ["📅 deadline  —  "]
        for delta, date, title in urgent_dl:
            if delta < 0:
                label = "⚠️ !"
            elif delta == 0:
                label = "🔴 "
            elif delta == 1:
                label = "🟡 Tomorrow"
            else:
                label = f"D-{delta}"
            lines.append(f"  {label} {title}")
        sections.append("\n".join(lines))

    conn = _get_db()
    if not conn:
        if sections:
            return f"T9 Brief — {now:%m/%d %H:%M}\n\n" + "\n\n".join(sections)
        return None

    # === 2. — 7+ , ===
    week_ago = (now - timedelta(days=7)).isoformat()
    try:
        stale = conn.execute(
            "SELECT id, filename, phase, updated_at FROM entities "
            "WHERE phase='individuating' AND updated_at < ? "
            "ORDER BY updated_at LIMIT 5", (week_ago,)
        ).fetchall()
        if stale:
            lines = ["🚧  — /suspended/ "]
            for r in stale:
                days = (now - datetime.fromisoformat(r["updated_at"])).days
                name = r["filename"].replace(".md", "")[:40]
                lines.append(f"  {name} ({days} )")
            sections.append("\n".join(lines))
    except Exception:
        pass

    # === 3. 24h state summary ===
    yesterday = (now - timedelta(hours=24)).isoformat()
    try:
        transitions = conn.execute(
            "SELECT t.from_phase, t.to_phase, e.filename FROM transitions t "
            "JOIN entities e ON t.entity_id = e.id "
            "WHERE t.timestamp >= ? ORDER BY t.timestamp DESC LIMIT 8",
            (yesterday,)
        ).fetchall()
        if transitions:
            lines = ["🔄 24h "]
            for t in transitions:
                name = t["filename"].replace(".md", "")[:35]
                lines.append(f"  {name}: {t['from_phase']}→{t['to_phase']}")
            sections.append("\n".join(lines))
    except Exception:
        pass

    # === 4. ===
    try:
        counts = {}
        for phase in ["preindividual", "tension_detected", "individuating", "stabilized"]:
            row = conn.execute(
                "SELECT COUNT() as c FROM entities WHERE phase=?", (phase,)
            ).fetchone()
            counts[phase] = row["c"] if row else 0

        if counts["preindividual"] > 20:
            sections.append(
                f"📥  \n  Preindividual {counts['preindividual']}items — "
                f"clean up/tidy \n  (next tidy: / 10:00)"
            )
    except Exception:
        counts = {"preindividual": 0, "individuating": 0, "stabilized": 0}

    # === 5. urgent (tension_detected) ===
    try:
        tension = conn.execute(
            "SELECT id, filename FROM entities "
            "WHERE phase='tension_detected' LIMIT 5"
        ).fetchall()
        if tension:
            lines = ["🔥 Tension  — check "]
            for r in tension:
                name = r["filename"].replace(".md", "")[:40]
                lines.append(f"  [{r['id']}] {name}")
            sections.append("\n".join(lines))
    except Exception:
        pass

    conn.close()

    # === ===
    if not sections:
        return None  # reportnot found = CEO

    header = f"T9 CEO Brief — {now:%m/%d %H:%M}\n"
    ind = counts.get("individuating", 0)
    pre = counts.get("preindividual", 0)
    stab = counts.get("stabilized", 0)
    footer = f"\n_{ind} active | {pre} inbox | {stab} stabilized_"
    return header + "\n\n".join(sections) + "\n" + footer


def main():
    brief = build_brief()
    if brief:
        if "--dry-run" in sys.argv:
            print(brief)
        else:
            tg_send(brief)
            print(f"[{datetime.now():%H:%M:%S}] CEO brief sent")
    else:
        print(f"[{datetime.now():%H:%M:%S}] Nothing to report — CEO ")


if __name__ == "__main__":
    with pipeline_run("ceo_brief"):
        main()
